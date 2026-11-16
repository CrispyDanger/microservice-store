import os
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import asyncpg
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

ADMIN_DB_URL = "postgres://order:order@order-db:5432/order"
TEST_DB_NAME = "order_test"


def _keypair() -> tuple[str, str]:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private = key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()
    public = key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private, public


PRIVATE_KEY, PUBLIC_KEY = _keypair()
OTHER_PRIVATE_KEY, _ = _keypair()

with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
    f.write(PUBLIC_KEY)

os.environ["ORDER_DATABASE_URL"] = f"postgres://order:order@order-db:5432/{TEST_DB_NAME}"
os.environ["ORDER_JWT_PUBLIC_KEY_PATH"] = f.name

from httpx import ASGITransport, AsyncClient  # noqa: E402
from tortoise import Tortoise  # noqa: E402

from order.db import TORTOISE_ORM  # noqa: E402
from order.dependencies import get_producer  # noqa: E402
from order.main import app  # noqa: E402


async def _ensure_test_db() -> None:
    conn = await asyncpg.connect(ADMIN_DB_URL)
    try:
        exists = await conn.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", TEST_DB_NAME)
        if not exists:
            await conn.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
async def db():
    await _ensure_test_db()
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas(safe=True)
    yield
    await Tortoise.close_connections()


@pytest.fixture(autouse=True)
async def clean_tables():
    conn = Tortoise.get_connection("default")
    await conn.execute_script("TRUNCATE orders, order_items, idempotency_keys CASCADE")


class FakeProducer:
    def __init__(self) -> None:
        self.sent: list[tuple[str, bytes, bytes]] = []

    async def send_and_wait(self, topic: str, key: bytes, value: bytes) -> None:
        self.sent.append((topic, key, value))


@pytest.fixture
def producer():
    fake = FakeProducer()
    app.dependency_overrides[get_producer] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_producer, None)


@pytest.fixture
async def client(producer):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def make_token() -> Callable[..., str]:
    def _make(
        user_id: UUID | None = None,
        *,
        role: str = "user",
        private_key: str = PRIVATE_KEY,
        expires_in: timedelta = timedelta(minutes=5),
    ) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(user_id or uuid4()),
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + expires_in,
        }
        return jwt.encode(claims, private_key, algorithm="RS256")

    return _make


def with_new_key(headers: dict) -> dict:
    return {**headers, "Idempotency-Key": str(uuid4())}


@pytest.fixture
def user_id() -> UUID:
    return uuid4()


@pytest.fixture
def auth_headers(make_token, user_id) -> dict:
    return {"Authorization": f"Bearer {make_token(user_id)}"}


@pytest.fixture
def order_payload() -> dict:
    return {
        "items": [
            {"product_id": str(uuid4()), "quantity": 2},
            {"product_id": str(uuid4()), "quantity": 1},
        ],
        "total": "29.97",
    }
