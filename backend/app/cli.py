"""Management CLI utilities.

Usage:
    python -m app.cli create-superuser admin@example.com 'StrongPass123!' --name Admin
    python -m app.cli seed-demo            # idempotent demo data
    python -m app.cli seed-demo --reset    # wipe everything, then re-seed
"""
from __future__ import annotations

import argparse
import asyncio

from sqlalchemy import select

import app.models  # noqa: F401 - register models
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import SessionLocal, engine
from app.models.user import Role, User
from app.services.bootstrap import seed_roles_and_permissions
from app.services.seed import DEMO_PASSWORD, seed_demo_data


async def create_superuser(email: str, password: str, name: str) -> int:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        await seed_roles_and_permissions(db)
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=name or "Administrator",
                hashed_password=hash_password(password),
                is_active=True,
                is_superuser=True,
            )
            db.add(user)
        else:
            user.email = email
            user.full_name = name or user.full_name
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.is_superuser = True

        owner = await db.scalar(select(Role).where(Role.slug == "owner"))
        if owner is not None and owner not in user.roles:
            user.roles.append(owner)

        await db.commit()
        await db.refresh(user)
        print(f"Superuser ready: {user.email} (id={user.id}, superuser={user.is_superuser})")
        return user.id


async def seed_demo(reset: bool) -> dict:
    if reset:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("Database reset: all tables dropped and recreated.")
    else:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async with SessionLocal() as db:
        summary = await seed_demo_data(db)

    print("\nDemo data ready. Login credentials:\n")
    print(f"  Superuser : {summary['admin_email']}   /   {summary['admin_password']}")
    print(f"  Demo users: {', '.join(summary['demo_emails'])}")
    print(f"              shared password: {DEMO_PASSWORD}\n")
    print("Try: GET /api/v1/dashboard/stats, GET /api/v1/projects, GET /api/v1/notifications")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="AICRM SaaS management CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    cs = sub.add_parser("create-superuser", help="Create or promote a superuser")
    cs.add_argument("email")
    cs.add_argument("password")
    cs.add_argument("--name", default="Administrator")

    sd = sub.add_parser("seed-demo", help="Seed rich demo data (idempotent)")
    sd.add_argument("--reset", action="store_true", help="Drop all tables before seeding")

    args = parser.parse_args()
    if args.command == "create-superuser":
        asyncio.run(create_superuser(args.email, args.password, args.name))
    elif args.command == "seed-demo":
        asyncio.run(seed_demo(args.reset))


if __name__ == "__main__":
    main()
