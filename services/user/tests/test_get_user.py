from uuid import uuid4

import pytest

from user.models import Role, User


@pytest.fixture
async def admin_headers(client, user_payload, registered) -> dict:
    """Promote the registered user to admin, then log in so the token carries role=admin."""
    await User.filter(id=registered["id"]).update(role=Role.ADMIN)
    resp = await client.post(
        "/auth/login",
        json={"email": user_payload["email"], "password": user_payload["password"]},
    )
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
async def other_user(client) -> dict:
    resp = await client.post(
        "/auth/register",
        json={
            "email": "other@example.com",
            "password": "password123",
            "first_name": "Other",
            "last_name": "Person",
        },
    )
    return resp.json()


async def test_requires_a_token(client, registered):
    resp = await client.get(f"/users/{registered['id']}")

    assert resp.status_code == 401


async def test_normal_user_gets_403(client, other_user, auth_headers):
    resp = await client.get(f"/users/{other_user['id']}", headers=auth_headers)

    assert resp.status_code == 403
    assert resp.json() == {"detail": "Not enough permissions"}


async def test_admin_can_get_another_user(client, other_user, admin_headers):
    resp = await client.get(f"/users/{other_user['id']}", headers=admin_headers)

    assert resp.status_code == 200
    assert resp.json() == other_user
    assert "password" not in resp.json()


async def test_admin_gets_404_for_unknown_user(client, admin_headers):
    resp = await client.get(f"/users/{uuid4()}", headers=admin_headers)

    assert resp.status_code == 404
    assert resp.json() == {"detail": "User not found"}


async def test_invalid_uuid_is_422(client, admin_headers):
    resp = await client.get("/users/not-a-uuid", headers=admin_headers)

    assert resp.status_code == 422


async def test_users_me_is_not_caught_by_the_user_id_route(client, registered, auth_headers):
    # If get_user.router were included before me.router, this would be a 422 ("me" isn't a UUID)
    resp = await client.get("/users/me", headers=auth_headers)

    assert resp.status_code == 200
    assert resp.json()["id"] == registered["id"]


async def test_demoted_admin_loses_access_on_next_request(client, registered, other_user, admin_headers):
    # The token still says role=admin, but require_role checks the user loaded from the DB
    await User.filter(id=registered["id"]).update(role=Role.USER)

    resp = await client.get(f"/users/{other_user['id']}", headers=admin_headers)

    assert resp.status_code == 403
