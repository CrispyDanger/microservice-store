from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
import pytest

from auth import AccessClaims, InvalidToken, decode_access_token


def test_valid_token_returns_typed_claims(keys, make_token):
    user_id = uuid4()

    claims = decode_access_token(make_token(sub=str(user_id), role="admin"), keys[1])

    assert isinstance(claims, AccessClaims)
    assert claims.user_id == user_id
    assert isinstance(claims.user_id, UUID)
    assert claims.role == "admin"
    assert claims.expires_at > datetime.now(UTC)


def test_token_signed_with_another_key_is_rejected(keys, other_keys, make_token):
    with pytest.raises(InvalidToken):
        decode_access_token(make_token(private_key=other_keys[0]), keys[1])


def test_tampered_token_is_rejected(keys, make_token):
    token = make_token()
    tampered = token[:-2] + ("A" if token[-2] != "A" else "B") + token[-1]

    with pytest.raises(InvalidToken):
        decode_access_token(tampered, keys[1])


def test_garbage_is_rejected(keys):
    with pytest.raises(InvalidToken):
        decode_access_token("not-a-jwt", keys[1])


def test_expired_token_is_rejected(keys, make_token):
    token = make_token(exp=datetime.now(UTC) - timedelta(seconds=1))

    with pytest.raises(InvalidToken):
        decode_access_token(token, keys[1])


@pytest.mark.parametrize("claim", ["exp", "sub", "type", "role"])
def test_missing_required_claim_is_rejected(keys, make_token, claim):
    with pytest.raises(InvalidToken):
        decode_access_token(make_token(drop=(claim,)), keys[1])


def test_non_access_token_type_is_rejected(keys, make_token):
    with pytest.raises(InvalidToken):
        decode_access_token(make_token(type="refresh"), keys[1])


def test_sub_that_is_not_a_uuid_is_rejected(keys, make_token):
    with pytest.raises(InvalidToken):
        decode_access_token(make_token(sub="not-a-uuid"), keys[1])


def test_alg_none_is_rejected(keys):
    exp = datetime.now(UTC) + timedelta(minutes=5)
    unsigned = jwt.encode(
        {"sub": str(uuid4()), "role": "admin", "type": "access", "exp": exp},
        key=None,
        algorithm="none",
    )

    with pytest.raises(InvalidToken):
        decode_access_token(unsigned, keys[1])


def test_hs256_signed_with_public_key_is_rejected(keys):
    # Algorithm confusion: an attacker knows the public key and uses it as an HMAC secret
    exp = datetime.now(UTC) + timedelta(minutes=5)
    try:
        forged = jwt.encode(
            {"sub": str(uuid4()), "role": "admin", "type": "access", "exp": exp},
            keys[1],
            algorithm="HS256",
        )
    except jwt.InvalidKeyError:
        return  # PyJWT refuses to create it at all, which also protects us

    with pytest.raises(InvalidToken):
        decode_access_token(forged, keys[1])
