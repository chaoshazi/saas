"""Default roles, permissions, and seed data."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.org import Organization
from app.models.user import Permission, Role

PERMISSIONS = [
    ("project.create", "Create project", "project", "create"),
    ("project.read", "Read project", "project", "read"),
    ("project.update", "Update project", "project", "update"),
    ("project.delete", "Delete project", "project", "delete"),
    ("task.create", "Create task", "task", "create"),
    ("task.read", "Read task", "task", "read"),
    ("task.update", "Update task", "task", "update"),
    ("task.delete", "Delete task", "task", "delete"),
    ("document.manage", "Manage documents", "document", "manage"),
    ("user.manage", "Manage users", "user", "manage"),
    ("billing.manage", "Manage billing", "billing", "manage"),
    ("settings.manage", "Manage settings", "settings", "manage"),
    ("audit.read", "Read audit logs", "audit", "read"),
]

ROLE_DEFS = {
    "owner": {"name": "Owner", "permissions": PERMISSIONS},
    "admin": {"name": "Admin", "permissions": [p for p in PERMISSIONS if p[0] != "settings.manage"]},
    "member": {
        "name": "Member",
        "permissions": [p for p in PERMISSIONS if p[0] in {
            "project.create", "project.read", "project.update",
            "task.create", "task.read", "task.update", "document.manage",
        }],
    },
    "guest": {"name": "Guest", "permissions": [p for p in PERMISSIONS if p[0] in {"project.read", "task.read"}]},
}


async def seed_roles_and_permissions(db: AsyncSession) -> None:
    perm_by_code: dict[str, Permission] = {}
    for code, name, resource, action in PERMISSIONS:
        perm = await db.scalar(select(Permission).where(Permission.code == code))
        if perm is None:
            perm = Permission(code=code, name=name, resource=resource, action=action)
            db.add(perm)
        perm_by_code[code] = perm

    await db.flush()

    for slug, definition in ROLE_DEFS.items():
        permissions = [perm_by_code[p[0]] for p in definition["permissions"]]
        role = await db.scalar(
            select(Role).where(Role.slug == slug).options(selectinload(Role.permissions))
        )
        if role is None:
            role = Role(slug=slug, name=definition["name"], is_system=True, permissions=permissions)
            db.add(role)
        else:
            role.name = definition["name"]
            role.permissions = permissions

    org = await db.scalar(select(Organization).where(Organization.slug == "default"))
    if org is None:
        db.add(Organization(name="My Workspace", slug="default"))

    await db.commit()
