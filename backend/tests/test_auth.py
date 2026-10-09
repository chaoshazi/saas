"""Auth and user flow tests."""
from __future__ import annotations


async def _register(client, unique: str, password: str = "Password123!"):
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": f"{unique}@example.com", "password": password, "full_name": "Test User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_login_me(client, unique: str) -> None:
    tokens = await _register(client, unique)
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me = await client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == f"{unique}@example.com"
    assert "member" in me.json()["role_slugs"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": f"{unique}@example.com", "password": "Password123!"},
    )
    assert login.status_code == 200


async def test_login_wrong_password(client, unique: str) -> None:
    await _register(client, unique)
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": f"{unique}@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_refresh_and_logout(client, unique: str) -> None:
    tokens = await _register(client, unique)
    refreshed = await client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    access = refreshed.json()["access_token"]

    headers = {"Authorization": f"Bearer {access}"}
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 200

    logout = await client.post("/api/v1/auth/logout", headers=headers)
    assert logout.status_code == 204
    assert (await client.get("/api/v1/auth/me", headers=headers)).status_code == 401
