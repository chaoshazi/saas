"""Billing, subscription, and payment callback endpoints."""
from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_permission
from app.core.exceptions import NotFoundError, ValidationError
from app.db.session import get_db
from app.integrations.payments import get_gateway
from app.models.billing import Order, Plan, Subscription
from app.models.user import User
from app.schemas.billing import OrderCreate, OrderRead, PlanRead, SubscriptionRead
from app.services.audit import audit

router = APIRouter(tags=["billing"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _period_end(interval: str, start: datetime) -> datetime:
    if interval == "year":
        return start + timedelta(days=365)
    return start + timedelta(days=30)


async def _extend_subscription(db: AsyncSession, plan: Plan) -> Subscription:
    subscription = await db.scalar(select(Subscription).order_by(Subscription.id.desc()).limit(1))
    now = _utcnow()
    if subscription is None or subscription.status in {"expired", "canceled"}:
        subscription = Subscription(
            plan_id=plan.id,
            status="active",
            current_period_start=now,
            current_period_end=_period_end(plan.interval, now),
        )
        db.add(subscription)
    else:
        subscription.plan_id = plan.id
        subscription.status = "active"
        subscription.current_period_end = _period_end(plan.interval, subscription.current_period_end)
    await db.commit()
    await db.refresh(subscription)
    return subscription


@router.get("/billing/plans", response_model=list[PlanRead])
async def list_plans(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PlanRead]:
    plans = (await db.scalars(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.amount_cents))).all()
    return [PlanRead.model_validate(plan) for plan in plans]


@router.get("/billing/subscription", response_model=SubscriptionRead | None)
async def get_subscription(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionRead | None:
    subscription = await db.scalar(select(Subscription).order_by(Subscription.id.desc()).limit(1))
    if subscription is None:
        return None
    return SubscriptionRead.model_validate(subscription)


@router.post("/billing/orders")
async def create_order(
    payload: OrderCreate,
    user: User = Depends(require_permission("billing.manage")),
    db: AsyncSession = Depends(get_db),
) -> dict:
    plan = await db.scalar(select(Plan).where(Plan.code == payload.plan_code))
    if plan is None or not plan.is_active:
        raise NotFoundError("Plan not found")
    order = Order(
        order_no=f"ORD{int(time.time())}{uuid.uuid4().hex[:8]}",
        plan_id=plan.id,
        amount_cents=plan.amount_cents,
        currency=plan.currency,
        channel=payload.channel,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    try:
        result = await get_gateway(payload.channel).create_payment(
            order.order_no, order.amount_cents, f"{plan.name} subscription"
        )
    except RuntimeError as exc:
        raise ValidationError(str(exc)) from exc
    await audit(db, actor_id=user.id, action="billing.order_create", resource_type="order", resource_id=order.order_no)
    return {"order": OrderRead.model_validate(order).model_dump(), "checkout_url": result.checkout_url}


@router.get("/billing/orders", response_model=list[OrderRead])
async def list_orders(
    user: User = Depends(require_permission("billing.manage")),
    db: AsyncSession = Depends(get_db),
) -> list[OrderRead]:
    orders = (await db.scalars(select(Order).order_by(Order.created_at.desc()))).all()
    return [OrderRead.model_validate(order) for order in orders]


@router.post("/payments/callbacks/alipay")
async def alipay_callback(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw = dict(await request.form())
    verified = await get_gateway("alipay").verify_callback(dict(raw))
    await _mark_paid(db, verified)
    return {"success": True}


@router.post("/payments/callbacks/wechat")
async def wechat_callback(request: Request, db: AsyncSession = Depends(get_db)) -> dict:
    raw = await request.json()
    verified = await get_gateway("wechat").verify_callback(raw)
    await _mark_paid(db, verified)
    return {"code": "SUCCESS", "message": "成功"}


async def _mark_paid(db: AsyncSession, payment: dict) -> None:
    order_no = payment.get("order_no")
    if not order_no:
        return
    order = await db.scalar(select(Order).where(Order.order_no == order_no))
    if order is None:
        return
    if order.status == "paid":
        return
    order.status = "paid"
    order.paid_at = _utcnow()
    plan = await db.get(Plan, order.plan_id)
    if plan is not None:
        await _extend_subscription(db, plan)
    await audit(db, actor_id=None, action="billing.payment_success", resource_type="order", resource_id=order_no)
