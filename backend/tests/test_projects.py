"""Project, task, and notification flow tests."""
from __future__ import annotations


async def _register(client, unique: str):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"{unique}@example.com", "password": "Password123!", "full_name": "Test User"},
    )
    assert response.status_code == 201
    return response.json()


async def _headers(client, unique: str) -> dict:
    tokens = await _register(client, unique)
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def test_project_and_task_lifecycle(client, unique: str) -> None:
    headers = await _headers(client, unique)
    key = unique.upper()

    created = await client.post(
        "/api/v1/projects",
        json={"name": "Test Project", "key": key, "description": "desc"},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    project = created.json()

    boards = await client.get(f"/api/v1/projects/{project['id']}/boards", headers=headers)
    assert boards.status_code == 200
    assert len(boards.json()) == 1
    board = boards.json()[0]
    assert len(board["columns"]) == 3

    task = await client.post(
        "/api/v1/tasks",
        json={"board_id": board["id"], "column_id": board["columns"][0]["id"], "title": "First task", "priority": "high"},
        headers=headers,
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]

    updated = await client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "in_progress", "version": task.json()["version"]},
        headers=headers,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["version"] == 2

    comment = await client.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"body": "hello"},
        headers=headers,
    )
    assert comment.status_code == 201

    comments = await client.get(f"/api/v1/tasks/{task_id}/comments", headers=headers)
    assert len(comments.json()) == 1

    listed = await client.get(f"/api/v1/tasks?project_id={project['id']}", headers=headers)
    assert len(listed.json()) == 1


async def test_optimistic_lock_conflict(client, unique: str) -> None:
    headers = await _headers(client, unique)
    project = (await client.post("/api/v1/projects", json={"name": "P", "key": unique.upper()}, headers=headers)).json()
    board = (await client.get(f"/api/v1/projects/{project['id']}/boards", headers=headers)).json()[0]
    task = (await client.post("/api/v1/tasks", json={"board_id": board["id"], "title": "t"}, headers=headers)).json()

    conflict = await client.patch(
        f"/api/v1/tasks/{task['id']}", json={"title": "changed", "version": 999}, headers=headers
    )
    assert conflict.status_code == 409
