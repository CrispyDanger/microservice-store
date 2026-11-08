from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


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


@pytest.fixture(scope="session")
def keys() -> tuple[str, str]:
    """(private, public) PEM pair; the lib only ever sees the public one."""
    return _keypair()


@pytest.fixture(scope="session")
def other_keys() -> tuple[str, str]:
    """A different pair, to simulate a token signed by someone else."""
    return _keypair()


@pytest.fixture
def make_token(keys) -> Callable[..., str]:
    """Build a token like the user service does; override or drop claims per test."""

    def _make(*, private_key: str | None = None, drop: tuple[str, ...] = (), **overrides) -> str:
        now = datetime.now(UTC)
        claims = {
            "sub": str(uuid4()),
            "role": "user",
            "type": "access",
            "iat": now,
            "exp": now + timedelta(minutes=5),
            **overrides,
        }
        for name in drop:
            claims.pop(name)
        return jwt.encode(claims, private_key or keys[0], algorithm="RS256")

    return _make
