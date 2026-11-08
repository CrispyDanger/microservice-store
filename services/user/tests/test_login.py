from user.models import RefreshToken
from user.security.tokens import decode_access_token, hash_refresh_token


async def login(client, email, password):
    return await client.post("/auth/login", json={"email": email, "password": password})


async def test_login_returns_token_pair(client, user_payload, registered):
    resp = await login(client, user_payload["email"], user_payload["password"])

    assert resp.status_code == 200
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert str(decode_access_token(body["access_token"]).user_id) == registered["id"]


async def test_login_is_case_insensitive_on_email(client, user_payload, registered):
    resp = await login(client, user_payload["email"].upper(), user_payload["password"])

    assert resp.status_code == 200


async def test_wrong_password_and_unknown_email_look_identical(client, user_payload, registered):
    wrong_pw = await login(client, user_payload["email"], "wrong-password")
    unknown = await login(client, "nobody@example.com", user_payload["password"])

    assert wrong_pw.status_code == unknown.status_code == 401
    assert wrong_pw.json() == unknown.json()


async def test_inactive_user_cannot_log_in(client, user_payload, registered):
    from user.models import User
    await User.filter(id=registered["id"]).update(is_active=False)

    resp = await login(client, user_payload["email"], user_payload["password"])

    assert resp.status_code == 401


async def test_login_stores_only_the_refresh_token_hash(tokens):
    raw = tokens["refresh_token"]
    row = await RefreshToken.get(token_hash=hash_refresh_token(raw))

    assert row.token_hash != raw
    assert row.revoked_at is None


async def test_each_login_creates_a_new_session(client, user_payload, registered):
    await login(client, user_payload["email"], user_payload["password"])
    await login(client, user_payload["email"], user_payload["password"])

    assert await RefreshToken.filter(user_id=registered["id"]).count() == 2
