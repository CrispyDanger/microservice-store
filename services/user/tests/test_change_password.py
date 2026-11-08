import pytest

from user.models import RefreshToken, User
from user.security.passwords import verify_password

NEW_PASSWORD = "brand-new-pass"


async def change(client, headers, old, new=NEW_PASSWORD):
    return await client.post(
        "/users/me/password",
        json={"old_password": old, "new_password": new},
        headers=headers,
    )


async def login(client, email, password):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_change_password_requires_a_token(client, user_payload):
    resp = await change(client, {}, user_payload["password"])

    assert resp.status_code == 401


async def test_change_password_returns_204(client, user_payload, auth_headers):
    resp = await change(client, auth_headers, user_payload["password"])

    assert resp.status_code == 204
    assert resp.content == b""


async def test_only_the_new_password_works_afterwards(client, user_payload, auth_headers):
    await change(client, auth_headers, user_payload["password"])

    old = await login(client, user_payload["email"], user_payload["password"])
    new = await login(client, user_payload["email"], NEW_PASSWORD)
    assert old.status_code == 401
    assert new.status_code == 200


async def test_new_password_is_stored_as_a_hash(client, user_payload, registered, auth_headers):
    await change(client, auth_headers, user_payload["password"])

    user = await User.get(id=registered["id"])
    assert user.password.startswith("$argon2id$")
    assert verify_password(NEW_PASSWORD, user.password)


async def test_wrong_old_password_is_rejected(client, user_payload, registered, auth_headers):
    resp = await change(client, auth_headers, "wrong-old-pass")

    assert resp.status_code == 401
    user = await User.get(id=registered["id"])
    assert verify_password(user_payload["password"], user.password)  # unchanged


@pytest.mark.parametrize("new", ["short", "x" * 129])
async def test_new_password_length_is_validated(client, user_payload, auth_headers, new):
    resp = await change(client, auth_headers, user_payload["password"], new)

    assert resp.status_code == 422


async def test_change_password_revokes_all_sessions(client, user_payload, registered, auth_headers):
    await login(client, user_payload["email"], user_payload["password"])  # a second session
    assert await RefreshToken.filter(user_id=registered["id"], revoked_at=None).count() == 2

    await change(client, auth_headers, user_payload["password"])

    assert await RefreshToken.filter(user_id=registered["id"], revoked_at=None).count() == 0


async def test_failed_change_does_not_revoke_sessions(client, registered, auth_headers):
    await change(client, auth_headers, "wrong-old-pass")

    assert await RefreshToken.filter(user_id=registered["id"], revoked_at=None).count() == 1
