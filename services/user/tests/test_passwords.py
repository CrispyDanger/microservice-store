from user.security.passwords import DUMMY_HASH, hash_password, verify_password


def test_correct_password_verifies():
    hashed = hash_password("secret123")

    assert verify_password("secret123", hashed)


def test_wrong_password_does_not_verify():
    hashed = hash_password("secret123")

    assert not verify_password("secret124", hashed)


def test_hash_is_argon2id_and_not_the_plain_password():
    hashed = hash_password("secret123")

    assert hashed.startswith("$argon2id$")
    assert "secret123" not in hashed


def test_same_password_gives_different_hashes():
    # Each hash has its own random salt, so equal passwords don't produce equal hashes
    assert hash_password("secret123") != hash_password("secret123")


def test_dummy_hash_is_a_real_hash():
    # Login verifies against it for unknown emails; it must be a valid hash that never matches
    assert DUMMY_HASH.startswith("$argon2id$")
    assert not verify_password("secret123", DUMMY_HASH)
