"""Demo seed data tests."""
from __future__ import annotations

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.billing import Plan
from app.models.project import Project, Task
from app.models.team import Team
from app.models.user import User
from app.services.seed import ADMIN_EMAIL, ADMIN_PASSWORD, seed_demo_data


async def test_seed_demo_data_is_idempotent(client) -> None:
    async with SessionLocal() as db:
        await seed_demo_data(db)
        await seed_demo_data(db)

    async with SessionLocal() as db:
        assert await db.scalar(select(func.count()).select_from(User)) == 5
        assert await db.scalar(select(func.count()).select_from(Team)) == 2
        assert await db.scalar(select(func.count()).select_from(Project)) == 2
        assert await db.scalar(select(func.count()).select_from(Plan)) == 3
        # 7 tasks in the AICRM project (incl. 2 subtasks) + 2 in the WEB project.
        assert await db.scalar(select(func.count()).select_from(Task)) == 9


async def test_seeded_admin_can_login_and_browse(client) -> None:
    async with SessionLocal() as db:
        await seed_demo_data(db)

    login = await client.post(
        "/api/v1/auth/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["is_superuser"] is True

    stats = await client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats.status_code == 200, stats.text
    body = stats.json()
    assert body["projects"] == 2
    assert body["users"] == 5
    assert body["teams"] == 2
    assert body["tasks"] == 9

    projects = await client.get("/api/v1/projects", headers=headers)
    assert projects.status_code == 200
    assert projects.json()["total"] == 2

    teams = await client.get("/api/v1/teams", headers=headers)
    assert teams.status_code == 200
    assert len(teams.json()) == 2

    notifications = await client.get("/api/v1/notifications", headers=headers)
    assert notifications.status_code == 200
    assert notifications.json()["total"] >= 2

    search = await client.get("/api/v1/search", headers=headers, params={"q": "AICRM"})
    assert search.status_code == 200
    assert search.json()["projects"]
