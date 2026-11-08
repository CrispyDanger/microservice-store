from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import jwt
import pytest

from user.exceptions import InvalidToken
from user.security import tokens


def fake_user():
    return SimpleNamespace(id=uuid4(), role="user")


def test_access_token_round_trip():
    user = fake_user()
    claims = tokens.decode_access_token(tokens.create_access_token(user))

    assert claims.user_id == user.id
    assert claims.role == "user"


def test_issued_token_has_the_access_type_claim():
    raw = jwt.decode(
        tokens.create_access_token(fake_user()), tokens._PUBLIC_KEY, algorithms=["RS256"]
    )

    assert raw["type"] == "access"


def test_tampered_token_is_rejected():
    token = tokens.create_access_token(fake_user())
    tampered = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]

    with pytest.raises(InvalidToken):
        tokens.decode_access_token(tampered)


def test_expired_token_is_rejected():
    past = datetime.now(UTC) - timedelta(minutes=1)
    token = jwt.encode(
        {"sub": "x", "type": "access", "exp": past}, tokens._PRIVATE_KEY, algorithm="RS256"
    )

    with pytest.raises(InvalidToken):
        tokens.decode_access_token(token)


def test_token_without_exp_is_rejected():
    token = jwt.encode({"sub": "x", "type": "access"}, tokens._PRIVATE_KEY, algorithm="RS256")

    with pytest.raises(InvalidToken):
        tokens.decode_access_token(token)


def test_non_access_token_type_is_rejected():
    exp = datetime.now(UTC) + timedelta(minutes=5)
    token = jwt.encode(
        {"sub": "x", "type": "refresh", "exp": exp}, tokens._PRIVATE_KEY, algorithm="RS256"
    )

    with pytest.raises(InvalidToken):
        tokens.decode_access_token(token)


def test_hs256_token_signed_with_public_key_is_rejected():
    # The classic algorithm-confusion attack: sign HS256 using the PUBLIC key as the secret
    exp = datetime.now(UTC) + timedelta(minutes=5)
    try:
        forged = jwt.encode(
            {"sub": "x", "type": "access", "exp": exp}, tokens._PUBLIC_KEY, algorithm="HS256"
        )
    except jwt.InvalidKeyError:
        return  # PyJWT refuses to even create it, which also counts as protected

    with pytest.raises(InvalidToken):
        tokens.decode_access_token(forged)


def test_refresh_tokens_are_random_and_hashed():
    raw1, hash1 = tokens.new_refresh_token()
    raw2, _ = tokens.new_refresh_token()

    assert raw1 != raw2
    assert hash1 == tokens.hash_refresh_token(raw1)
    assert raw1 not in hash1
