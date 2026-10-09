"""Tests for the extended backend surface."""
from __future__ import annotations


async def _register(client, unique: str, password: str = "Password123!"):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"{unique}@example.com", "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _headers(client, unique: str):
    tokens = await _register(client, unique)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_teams_lifecycle(client, unique: str) -> None:
    headers = await _headers(client, unique)
    created = await client.post("/api/v1/teams", json={"name": "Core", "description": "core team"}, headers=headers)
    assert created.status_code == 201, created.text
    team_id = created.json()["id"]

    listed = await client.get("/api/v1/teams", headers=headers)
    assert listed.status_code == 200
    assert any(t["id"] == team_id for t in listed.json())

    updated = await client.patch(f"/api/v1/teams/{team_id}", json={"name": "Core 2"}, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["name"] == "Core 2"

    deleted = await client.delete(f"/api/v1/teams/{team_id}", headers=headers)
    assert deleted.status_code == 204


async def test_labels_and_subtasks(client, unique: str) -> None:
    headers = await _headers(client, unique)
    project = (await client.post("/api/v1/projects", json={"name": "P", "key": unique.upper()}, headers=headers)).json()
    board = (await client.get(f"/api/v1/projects/{project['id']}/boards", headers=headers)).json()[0]

    label = await client.post(f"/api/v1/projects/{project['id']}/labels", json={"name": "bug", "color": "#f00"}, headers=headers)
    assert label.status_code == 201, label.text
    label_id = label.json()["id"]

    task = (await client.post("/api/v1/tasks", json={"board_id": board["id"], "title": "parent"}, headers=headers)).json()

    assigned = await client.post(f"/api/v1/tasks/{task['id']}/labels?label_id={label_id}", headers=headers)
    assert assigned.status_code == 200
    labels = await client.get(f"/api/v1/tasks/{task['id']}/labels", headers=headers)
    assert len(labels.json()) == 1

    subtask = await client.post(f"/api/v1/tasks/{task['id']}/subtasks", json={"title": "sub"}, headers=headers)
    assert subtask.status_code == 201, subtask.text
    subtasks = await client.get(f"/api/v1/tasks/{task['id']}/subtasks", headers=headers)
    assert len(subtasks.json()) == 1


async def test_preferences_and_dashboard(client, unique: str) -> None:
    headers = await _headers(client, unique)
    pref = await client.put(
        "/api/v1/notifications/preferences",
        json={"channel": "email", "event_type": "task.assigned", "enabled": False},
        headers=headers,
    )
    assert pref.status_code == 200
    prefs = await client.get("/api/v1/notifications/preferences", headers=headers)
    assert any(p["channel"] == "email" for p in prefs.json())

    stats = await client.get("/api/v1/dashboard/stats", headers=headers)
    assert stats.status_code == 200
    assert set(["projects", "tasks", "users"]).issubset(stats.json().keys())


async def test_password_reset_flow(client, unique: str) -> None:
    await _register(client, unique, "OldPassword123!")
    requested = await client.post("/api/v1/auth/password/reset-request", json={"email": f"{unique}@example.com"})
    assert requested.status_code == 200
    token = requested.json()["token"]

    reset = await client.post(
        "/api/v1/auth/password/reset",
        json={"token": token, "new_password": "NewPassword123!"},
    )
    assert reset.status_code == 204

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": f"{unique}@example.com", "password": "NewPassword123!"},
    )
    assert login.status_code == 200
