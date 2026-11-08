import asyncio
from uuid import UUID

import pytest

from user.exceptions import EmailTaken
from user.models import Role, User
from user.schemas.user import RegisterInput
from user.security.passwords import verify_password
from user.services.register import register_user

# --- Happy path -------------------------------------------------------------


async def test_register_returns_201_and_the_user(client, user_payload):
    resp = await client.post("/auth/register", json=user_payload)

    assert resp.status_code == 201
    body = resp.json()
    UUID(body["id"])  # raises if it isn't a valid UUID
    assert body["email"] == user_payload["email"]
    assert body["first_name"] == "Artem"
    assert body["last_name"] == "Yakovenko"
    assert body["role"] == "user"  # default role
    assert "created_at" in body


async def test_register_response_never_contains_the_password(client, user_payload):
    resp = await client.post("/auth/register", json=user_payload)

    body = resp.json()
    assert "password" not in body
    assert "password_hash" not in body
    assert user_payload["password"] not in resp.text


async def test_register_stores_a_hash_not_the_password(client, user_payload):
    await client.post("/auth/register", json=user_payload)

    user = await User.get(email=user_payload["email"])
    stored = user.password  # the column is named `password` but holds the Argon2 hash
    assert stored != user_payload["password"]
    assert stored.startswith("$argon2id$")
    assert verify_password(user_payload["password"], stored)


async def test_register_creates_an_active_user(client, user_payload):
    await client.post("/auth/register", json=user_payload)

    user = await User.get(email=user_payload["email"])
    assert user.is_active
    assert user.role == Role.USER


async def test_register_lowercases_the_email(client, user_payload):
    resp = await client.post("/auth/register", json={**user_payload, "email": "Artem@Example.COM"})

    assert resp.status_code == 201
    assert resp.json()["email"] == "artem@example.com"


# --- Duplicate email ----------------------------------------------------------


async def test_register_same_email_twice_returns_409(client, user_payload, registered):
    resp = await client.post("/auth/register", json=user_payload)

    assert resp.status_code == 409
    assert resp.json() == {"detail": "Email is already registered"}


async def test_register_same_email_different_case_returns_409(client, user_payload, registered):
    resp = await client.post("/auth/register", json={**user_payload, "email": "ARTEM@example.com"})

    assert resp.status_code == 409


async def test_failed_duplicate_does_not_create_a_second_user(client, user_payload, registered):
    await client.post("/auth/register", json=user_payload)

    assert await User.filter(email=user_payload["email"]).count() == 1


async def test_concurrent_registrations_create_only_one_user(client, user_payload):
    # Both requests can pass the exists() check at the same moment; the unique
    # constraint + IntegrityError handling must still turn the loser into a 409.
    responses = await asyncio.gather(
        *(client.post("/auth/register", json=user_payload) for _ in range(5))
    )

    codes = sorted(r.status_code for r in responses)
    assert codes == [201, 409, 409, 409, 409]
    assert await User.filter(email=user_payload["email"]).count() == 1


# --- Validation (422 = rejected before any of our code runs) -------------------


@pytest.mark.parametrize(
    "field, value",
    [
        ("email", "not-an-email"),
        ("email", ""),
        ("password", "short"),  # under 8 characters
        ("password", "x" * 129),  # over 128: protects the CPU from huge Argon2 inputs
        ("first_name", ""),
        ("last_name", ""),
        ("first_name", "x" * 256),
    ],
)
async def test_register_rejects_invalid_field(client, user_payload, field, value):
    resp = await client.post("/auth/register", json={**user_payload, field: value})

    assert resp.status_code == 422
    assert await User.all().count() == 0


@pytest.mark.parametrize("missing", ["email", "password", "first_name", "last_name"])
async def test_register_rejects_missing_field(client, user_payload, missing):
    body = {k: v for k, v in user_payload.items() if k != missing}

    resp = await client.post("/auth/register", json=body)

    assert resp.status_code == 422


async def test_register_accepts_password_at_the_limits(client, user_payload):
    short = await client.post("/auth/register", json={**user_payload, "password": "x" * 8})
    long = await client.post(
        "/auth/register",
        json={**user_payload, "email": "other@example.com", "password": "x" * 128},
    )

    assert short.status_code == 201
    assert long.status_code == 201


# --- Service layer, without HTTP -------------------------------------------------


async def test_register_user_service_raises_email_taken(user_payload):
    data = RegisterInput(**user_payload)
    await register_user(data)

    with pytest.raises(EmailTaken):
        await register_user(data)
