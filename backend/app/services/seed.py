"""Demo data seeding for local exploration, QA, and sales demos.

``seed_demo_data`` is idempotent (get-or-create) so it is safe to run on every
startup. Pass ``reset=True`` (CLI ``--reset``) to wipe existing data first.

The seeded dataset intentionally covers every major feature so a fresh install
is immediately usable: users/roles, teams, projects + kanban boards, tasks with
labels, subtasks and comments, versioned documents, notifications, billing
plans/orders and integrations.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.base import utcnow
from app.models.billing import Order, Plan, Subscription
from app.models.document import Document, DocumentVersion
from app.models.label import Label
from app.models.notification import Notification, NotificationPreference
from app.models.org import Organization, SystemSetting
from app.models.project import (
    Activity,
    Board,
    BoardColumn,
    Project,
    ProjectMember,
    Task,
    TaskComment,
)
from app.models.system import Integration
from app.models.team import Team
from app.models.user import Role, User
from app.services.bootstrap import seed_roles_and_permissions

logger = logging.getLogger(__name__)

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASSWORD = "Admin123456!"
DEMO_PASSWORD = "Demo123456!"

DEMO_USERS = [
    # email, full name, password, role slug, is_superuser
    (ADMIN_EMAIL, "系统管理员", ADMIN_PASSWORD, "owner", True),
    ("pm@example.com", "李雷 (产品经理)", DEMO_PASSWORD, "member", False),
    ("dev1@example.com", "韩梅梅 (前端工程师)", DEMO_PASSWORD, "member", False),
    ("dev2@example.com", "王强 (后端工程师)", DEMO_PASSWORD, "member", False),
    ("guest@example.com", "访客用户", DEMO_PASSWORD, "guest", False),
]

PLANS = [
    dict(code="free", name="免费版", interval="month", amount_cents=0, max_users=5, max_projects=3, max_storage_gb=1),
    dict(code="pro", name="专业版", interval="month", amount_cents=9900, max_users=50, max_projects=100, max_storage_gb=50),
    dict(code="enterprise", name="旗舰版", interval="year", amount_cents=299900, max_users=500, max_projects=1000, max_storage_gb=500),
]

LABEL_DEFS = [
    ("缺陷", "#ef4444"),
    ("新功能", "#3b82f6"),
    ("紧急", "#f97316"),
    ("文档", "#22c55e"),
    ("优化", "#a855f7"),
]

PREFS = [("in_app", "task"), ("email", "task"), ("wecom", "task"), ("in_app", "comment")]


async def _ensure_user(
    db: AsyncSession,
    email: str,
    full_name: str,
    password: str,
    role_slug: str,
    *,
    is_superuser: bool = False,
) -> User:
    role = await db.scalar(select(Role).where(Role.slug == role_slug))
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            is_active=True,
            is_superuser=is_superuser,
            locale="zh",
        )
        if role is not None:
            user.roles.append(role)
        db.add(user)
        await db.flush()
    else:
        if not user.hashed_password:
            user.hashed_password = hash_password(password)
        if is_superuser:
            user.is_superuser = True
        if role is not None and role not in user.roles:
            user.roles.append(role)
    return user


async def _ensure_project(
    db: AsyncSession, *, key: str, name: str, description: str, owner: User, due_in_days: int = 30
) -> Project:
    project = await db.scalar(select(Project).where(Project.key == key))
    if project is not None:
        return project
    project = Project(
        name=name,
        key=key,
        description=description,
        owner_id=owner.id,
        due_date=utcnow() + timedelta(days=due_in_days),
    )
    db.add(project)
    await db.flush()
    return project


async def _ensure_board(db: AsyncSession, project: Project, name: str, column_names: list[str]) -> Board:
    board = await db.scalar(select(Board).where(Board.project_id == project.id, Board.name == name))
    if board is None:
        board = Board(project_id=project.id, name=name, position=0)
        for index, column_name in enumerate(column_names):
            board.columns.append(BoardColumn(name=column_name, position=index))
        db.add(board)
        await db.flush()
        return board

    existing = {column.name for column in board.columns}
    for index, column_name in enumerate(column_names):
        if column_name not in existing:
            board.columns.append(BoardColumn(name=column_name, position=index))
    await db.flush()
    board.columns.sort(key=lambda column: column.position)
    return board


async def _ensure_label(db: AsyncSession, project: Project, name: str, color: str) -> Label:
    label = await db.scalar(select(Label).where(Label.project_id == project.id, Label.name == name))
    if label is None:
        label = Label(project_id=project.id, name=name, color=color)
        db.add(label)
        await db.flush()
    return label


async def _ensure_task(
    db: AsyncSession,
    *,
    project: Project,
    column: BoardColumn | None,
    creator: User,
    title: str,
    description: str | None = None,
    assignee: User | None = None,
    priority: str = "medium",
    status: str = "open",
    position: int = 0,
    due_in_days: int | None = None,
    parent: Task | None = None,
    labels: list[Label] | tuple[Label, ...] = (),
) -> Task:
    task = await db.scalar(select(Task).where(Task.project_id == project.id, Task.title == title))
    if task is not None:
        return task
    task = Task(
        project_id=project.id,
        column_id=column.id if column else None,
        parent_id=parent.id if parent else None,
        creator_id=creator.id,
        assignee_id=assignee.id if assignee else None,
        title=title,
        description=description,
        priority=priority,
        status=status,
        position=position,
        due_date=utcnow() + timedelta(days=due_in_days) if due_in_days is not None else None,
    )
    for label in labels:
        task.labels.append(label)
    db.add(task)
    await db.flush()
    return task


async def _ensure_comment(db: AsyncSession, task: Task, author: User, body: str) -> None:
    existing = await db.scalar(
        select(TaskComment).where(TaskComment.task_id == task.id, TaskComment.body == body)
    )
    if existing is None:
        db.add(TaskComment(task_id=task.id, author_id=author.id, body=body))


async def _ensure_notification(
    db: AsyncSession, *, user: User, title: str, body: str, type_: str, actor: User | None = None
) -> None:
    existing = await db.scalar(
        select(Notification).where(Notification.user_id == user.id, Notification.title == title)
    )
    if existing is None:
        db.add(
            Notification(
                user_id=user.id,
                actor_id=actor.id if actor else None,
                title=title,
                body=body,
                type=type_,
            )
        )


async def seed_demo_data(db: AsyncSession) -> dict:
    """Populate a rich, idempotent demo dataset. Returns a summary dict."""
    await seed_roles_and_permissions(db)

    org = await db.scalar(select(Organization).where(Organization.slug == "default"))
    if org is None:
        org = Organization(name="示例工作空间", slug="default")
        db.add(org)
    else:
        org.name = org.name or "示例工作空间"

    users: dict[str, User] = {}
    for email, full_name, password, role_slug, is_superuser in DEMO_USERS:
        users[email] = await _ensure_user(
            db, email, full_name, password, role_slug, is_superuser=is_superuser
        )
    await db.flush()

    admin = users[ADMIN_EMAIL]
    pm = users["pm@example.com"]
    dev1 = users["dev1@example.com"]
    dev2 = users["dev2@example.com"]
    guest = users["guest@example.com"]

    # --- Teams -------------------------------------------------------------
    team = await db.scalar(select(Team).where(Team.name == "产品研发团队"))
    if team is None:
        team = Team(
            name="产品研发团队",
            description="负责 AICRM 核心产品的需求、设计与研发",
            owner_id=admin.id,
        )
        for member in (admin, pm, dev1, dev2):
            team.members.append(member)
        db.add(team)
        await db.flush()
    else:
        for member in (admin, pm, dev1, dev2):
            if member not in team.members:
                team.members.append(member)

    design_team = await db.scalar(select(Team).where(Team.name == "设计团队"))
    if design_team is None:
        design_team = Team(name="设计团队", description="UI / UX 设计", owner_id=pm.id)
        for member in (pm, dev1):
            design_team.members.append(member)
        db.add(design_team)
        await db.flush()
    else:
        for member in (pm, dev1):
            if member not in design_team.members:
                design_team.members.append(member)

    # --- Projects & boards -------------------------------------------------
    project = await _ensure_project(
        db,
        key="AICRM",
        name="AICRM 客户管理系统",
        description="面向销售的客户关系管理平台，包含线索、商机、合同全流程。",
        owner=admin,
        due_in_days=45,
    )
    board = await _ensure_board(
        db, project, "迭代看板", ["待办", "进行中", "待评审", "已完成"]
    )
    columns = {column.name: column for column in board.columns}

    for name, color in LABEL_DEFS:
        await _ensure_label(db, project, name, color)

    labels = {
        label.name: label
        for label in (
            await db.scalars(select(Label).where(Label.project_id == project.id))
        ).all()
    }

    for member, role in ((admin, "admin"), (pm, "admin"), (dev1, "member"), (dev2, "member")):
        exists = await db.scalar(
            select(ProjectMember).where(
                ProjectMember.project_id == project.id, ProjectMember.user_id == member.id
            )
        )
        if exists is None:
            db.add(ProjectMember(project_id=project.id, user_id=member.id, role=role))
    await db.flush()

    design_doc_task = await _ensure_task(
        db,
        project=project,
        column=columns["进行中"],
        creator=pm,
        title="编写客户画像功能设计方案",
        description="输出客户画像的数据结构、字段来源与展示方案，并与研发评审。",
        assignee=pm,
        priority="high",
        position=0,
        due_in_days=5,
        labels=[labels["文档"], labels["紧急"]],
    )
    await _ensure_task(
        db,
        project=project,
        column=columns["待办"],
        creator=pm,
        title="整理客户画像字段清单",
        assignee=dev1,
        priority="medium",
        parent=design_doc_task,
    )
    await _ensure_task(
        db,
        project=project,
        column=columns["已完成"],
        creator=pm,
        title="完成字段来源梳理",
        assignee=pm,
        priority="low",
        parent=design_doc_task,
    )

    await _ensure_task(
        db,
        project=project,
        column=columns["进行中"],
        creator=admin,
        title="线索列表支持批量导入",
        description="支持 Excel 批量导入线索，含字段校验与错误报告导出。",
        assignee=dev2,
        priority="high",
        position=1,
        due_in_days=8,
        labels=[labels["新功能"]],
    )
    await _ensure_task(
        db,
        project=project,
        column=columns["待办"],
        creator=dev2,
        title="修复登录页验证码偶发失效",
        description="低频复现，怀疑与 Redis 过期时间设置有关。",
        assignee=dev1,
        priority="high",
        position=2,
        due_in_days=2,
        labels=[labels["缺陷"], labels["紧急"]],
    )
    completed_task = await _ensure_task(
        db,
        project=project,
        column=columns["已完成"],
        creator=admin,
        title="搭建项目骨架与 CI",
        description="完成前后端工程初始化、代码规范与自动化测试流水线。",
        assignee=admin,
        priority="medium",
        status="done",
        position=3,
        labels=[labels["优化"]],
    )
    await _ensure_task(
        db,
        project=project,
        column=columns["待评审"],
        creator=dev1,
        title="移动端看板拖拽体验优化",
        assignee=dev1,
        priority="medium",
        position=4,
        labels=[labels["优化"]],
    )

    await _ensure_comment(db, design_doc_task, dev1, "前端这边建议画布用虚拟滚动，字段多了也不会卡。")
    await _ensure_comment(db, design_doc_task, pm, "好的，本周五前给出高保真原型。")
    await _ensure_comment(db, completed_task, admin, "CI 已全绿，可以进入下一个迭代。")
    await db.flush()

    # --- Second project ----------------------------------------------------
    web_project = await _ensure_project(
        db,
        key="WEB",
        name="官网改版",
        description="公司官网 2.0 改版，聚焦品牌形象与线索转化。",
        owner=pm,
        due_in_days=20,
    )
    web_board = await _ensure_board(db, web_project, "任务看板", ["需求池", "设计中", "开发中", "已上线"])
    web_columns = {column.name: column for column in web_board.columns}
    for name, color in LABEL_DEFS[:3]:
        await _ensure_label(db, web_project, name, color)
    await db.flush()

    await _ensure_task(
        db,
        project=web_project,
        column=web_columns["设计中"],
        creator=pm,
        title="首页视觉稿设计",
        assignee=dev1,
        priority="medium",
        due_in_days=6,
    )
    await _ensure_task(
        db,
        project=web_project,
        column=web_columns["需求池"],
        creator=pm,
        title="梳理官网信息架构",
        assignee=pm,
        priority="low",
        due_in_days=10,
    )

    # --- Documents ---------------------------------------------------------
    doc = await db.scalar(select(Document).where(Document.title == "AICRM 产品需求文档"))
    if doc is None:
        doc = Document(
            project_id=project.id,
            creator_id=pm.id,
            title="AICRM 产品需求文档",
            content="# AICRM 产品需求文档\n\n## 1. 背景\n面向中小销售的轻量 CRM。\n\n## 2. 目标\n线索转化率提升 20%。",
            is_published=True,
        )
        db.add(doc)
        await db.flush()
        db.add(
            DocumentVersion(
                document_id=doc.id,
                author_id=pm.id,
                version=1,
                content=doc.content,
                change_note="初稿",
            )
        )
    api_doc = await db.scalar(select(Document).where(Document.title == "API 接口说明"))
    if api_doc is None:
        api_doc = Document(
            project_id=project.id,
            creator_id=dev2.id,
            title="API 接口说明",
            content="# API 接口说明\n\n所有接口以 `/api/v1` 为前缀，使用 JWT Bearer 认证。",
            is_published=False,
        )
        db.add(api_doc)
        await db.flush()
        db.add(
            DocumentVersion(
                document_id=api_doc.id,
                author_id=dev2.id,
                version=1,
                content=api_doc.content,
                change_note="创建接口文档",
            )
        )

    # --- Activities --------------------------------------------------------
    activity_marker = await db.scalar(select(Activity).limit(1))
    if activity_marker is None:
        db.add_all(
            [
                Activity(project_id=project.id, actor_id=admin.id, action="project.create", target_type="project", target_id=str(project.id)),
                Activity(project_id=project.id, actor_id=pm.id, action="task.create", target_type="task", target_id=str(design_doc_task.id)),
                Activity(project_id=web_project.id, actor_id=pm.id, action="project.create", target_type="project", target_id=str(web_project.id)),
            ]
        )

    # --- Notifications -----------------------------------------------------
    await _ensure_notification(
        db, user=admin, title="欢迎使用 AICRM SaaS", body="这是一条演示通知，可点击右侧铃铛查看。", type_="info"
    )
    await _ensure_notification(
        db, user=admin, title="任务已分配给你", body="线索列表支持批量导入", type_="task", actor=pm
    )
    await _ensure_notification(
        db, user=pm, title="有人评论了你的任务", body="前端这边建议画布用虚拟滚动，字段多了也不会卡。", type_="comment", actor=dev1
    )
    await _ensure_notification(
        db, user=dev1, title="新任务已分配", body="修复登录页验证码偶发失效", type_="task", actor=dev2
    )
    await _ensure_notification(
        db, user=guest, title="欢迎体验 AICRM", body="你当前是访客角色，仅有只读权限。", type_="info"
    )

    # --- Notification preferences -----------------------------------------
    for user in (admin, pm, dev1, dev2, guest):
        for channel, event_type in PREFS:
            exists = await db.scalar(
                select(NotificationPreference).where(
                    NotificationPreference.user_id == user.id,
                    NotificationPreference.channel == channel,
                    NotificationPreference.event_type == event_type,
                )
            )
            if exists is None:
                db.add(
                    NotificationPreference(
                        user_id=user.id, channel=channel, event_type=event_type, enabled=True
                    )
                )

    # --- Billing -----------------------------------------------------------
    plans: dict[str, Plan] = {}
    for definition in PLANS:
        plan = await db.scalar(select(Plan).where(Plan.code == definition["code"]))
        if plan is None:
            plan = Plan(**definition)
            db.add(plan)
            await db.flush()
        plans[definition["code"]] = plan

    pro = plans["pro"]
    subscription = await db.scalar(select(Subscription).order_by(Subscription.id.desc()).limit(1))
    if subscription is None:
        now = utcnow()
        db.add(
            Subscription(
                plan_id=pro.id,
                status="active",
                current_period_start=now,
                current_period_end=now + timedelta(days=30),
                auto_renew=True,
            )
        )

    order = await db.scalar(select(Order).where(Order.order_no == "DEMO-ORDER-0001"))
    if order is None:
        db.add(
            Order(
                order_no="DEMO-ORDER-0001",
                plan_id=pro.id,
                amount_cents=pro.amount_cents,
                currency="CNY",
                status="paid",
                channel="alipay",
                paid_at=utcnow(),
            )
        )
    pending = await db.scalar(select(Order).where(Order.order_no == "DEMO-ORDER-0002"))
    if pending is None:
        db.add(
            Order(
                order_no="DEMO-ORDER-0002",
                plan_id=plans["enterprise"].id,
                amount_cents=plans["enterprise"].amount_cents,
                currency="CNY",
                status="pending",
                channel="wechat",
            )
        )

    # --- Integrations ------------------------------------------------------
    for provider, name in (("wecom", "企业微信"), ("smtp", "邮件服务"), ("alipay", "支付宝"), ("wechat", "微信支付")):
        integration = await db.scalar(select(Integration).where(Integration.provider == provider))
        if integration is None:
            db.add(Integration(provider=provider, name=name, enabled=False, config_json="{}"))

    # --- System settings ---------------------------------------------------
    settings_seed = {
        "site.name": "AICRM SaaS",
        "site.locale": "zh",
        "security.password_min_length": "8",
        "billing.currency": "CNY",
    }
    for key, value in settings_seed.items():
        setting = await db.scalar(select(SystemSetting).where(SystemSetting.key == key))
        if setting is None:
            db.add(SystemSetting(key=key, value=value, is_public=key.startswith("site.")))

    await db.commit()

    summary = {
        "users": len(DEMO_USERS),
        "teams": 2,
        "projects": 2,
        "admin_email": ADMIN_EMAIL,
        "admin_password": ADMIN_PASSWORD,
        "demo_password": DEMO_PASSWORD,
        "demo_emails": [email for email, *_ in DEMO_USERS if email != ADMIN_EMAIL],
    }
    logger.info("demo data seeded: %s", summary)
    return summary
