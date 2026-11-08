from datetime import UTC, datetime, timedelta

import jwt

from user.models import User
from user.security import tokens as token_lib

# --- Authentication (who are you?) ------------------------------------------------


async def test_me_requires_a_token(client):
    resp = await client.get("/users/me")

    assert resp.status_code == 401
    assert resp.headers["www-authenticate"] == "Bearer"


async def test_me_rejects_a_garbage_token(client):
    resp = await client.get("/users/me", headers={"Authorization": "Bearer not-a-jwt"})

    assert resp.status_code == 401


async def test_me_rejects_a_non_bearer_scheme(client, tokens):
    resp = await client.get(
        "/users/me", headers={"Authorization": f"Basic {tokens['access_token']}"}
    )

    assert resp.status_code == 401


async def test_me_rejects_an_expired_token(client, registered):
    past = datetime.now(UTC) - timedelta(minutes=1)
    expired = jwt.encode(
        {"sub": registered["id"], "type": "access", "exp": past},
        token_lib._PRIVATE_KEY,
        algorithm="RS256",
    )

    resp = await client.get("/users/me", headers={"Authorization": f"Bearer {expired}"})

    assert resp.status_code == 401


async def test_token_of_a_deleted_user_is_rejected(client, registered, auth_headers):
    await User.filter(id=registered["id"]).delete()

    resp = await client.get("/users/me", headers=auth_headers)

    assert resp.status_code == 401


async def test_deactivated_user_is_locked_out_immediately(client, registered, auth_headers):
    # The token itself is still valid; the DB lookup in get_current_user catches this
    await User.filter(id=registered["id"]).update(is_active=False)

    resp = await client.get("/users/me", headers=auth_headers)

    assert resp.status_code == 401


# --- GET /users/me ------------------------------------------------------------------


async def test_me_returns_the_current_user(client, registered, auth_headers):
    resp = await client.get("/users/me", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == registered
    assert "password" not in resp.json()


# --- PATCH /users/me ----------------------------------------------------------------


async def test_patch_requires_a_token(client):
    resp = await client.patch("/users/me", json={"first_name": "New"})

    assert resp.status_code == 401


async def test_patch_changes_only_sent_fields(client, registered, auth_headers):
    resp = await client.patch("/users/me", json={"first_name": "New"}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["first_name"] == "New"
    assert resp.json()["last_name"] == registered["last_name"]

    user = await User.get(id=registered["id"])  # really saved, not just in the response
    assert user.first_name == "New"
    assert user.last_name == registered["last_name"]


async def test_patch_both_names(client, auth_headers):
    resp = await client.patch(
        "/users/me", json={"first_name": "A", "last_name": "B"}, headers=auth_headers
    )

    assert resp.status_code == 200
    assert (resp.json()["first_name"], resp.json()["last_name"]) == ("A", "B")


async def test_patch_with_empty_body_changes_nothing(client, registered, auth_headers):
    resp = await client.patch("/users/me", json={}, headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json() == registered


async def test_patch_ignores_fields_that_are_not_editable(client, registered, auth_headers):
    # email, role and password are not in UserUpdateInput, so Pydantic drops them
    resp = await client.patch(
        "/users/me",
        json={"email": "hacker@example.com", "role": "admin", "password": "x" * 10},
        headers=auth_headers,
    )

    assert resp.status_code == 200
    user = await User.get(id=registered["id"])
    assert user.email == registered["email"]
    assert user.role == "user"


async def test_patch_rejects_empty_name(client, auth_headers):
    resp = await client.patch("/users/me", json={"first_name": ""}, headers=auth_headers)

    assert resp.status_code == 422


async def test_patch_rejects_too_long_name(client, auth_headers):
    resp = await client.patch("/users/me", json={"last_name": "x" * 256}, headers=auth_headers)

    assert resp.status_code == 422
