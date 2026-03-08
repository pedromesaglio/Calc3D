import pytest

from app.auth import hash_password, verify_password


class TestHashPassword:
    def test_returns_salt_and_hash(self):
        result = hash_password("mypassword")
        assert "$" in result
        parts = result.split("$")
        assert len(parts) == 2
        assert len(parts[0]) == 32  # salt: 16 bytes hex = 32 chars
        assert len(parts[1]) == 64  # sha256 hex = 64 chars

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # different salts


class TestVerifyPassword:
    def test_correct_password_verifies(self):
        stored = hash_password("correcthorse")
        assert verify_password("correcthorse", stored) is True

    def test_wrong_password_fails(self):
        stored = hash_password("correcthorse")
        assert verify_password("wrong", stored) is False

    def test_malformed_stored_returns_false(self):
        assert verify_password("password", "notvalid") is False

    def test_empty_password_handled(self):
        stored = hash_password("")
        assert verify_password("", stored) is True
        assert verify_password("notempty", stored) is False
