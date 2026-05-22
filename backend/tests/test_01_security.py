"""
Tests unitaires purs — sécurité (sans base de données).
"""
import time
import pytest
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token, decode_token,
)


class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        pw = "MonMotDePasse123!"
        assert hash_password(pw) != pw

    def test_verify_correct_password(self):
        pw = "MonMotDePasse123!"
        assert verify_password(pw, hash_password(pw)) is True

    def test_verify_wrong_password(self):
        assert verify_password("mauvais", hash_password("bon")) is False

    def test_two_hashes_are_different(self):
        """bcrypt génère un salt différent à chaque fois."""
        pw = "SamePw1!"
        assert hash_password(pw) != hash_password(pw)

    def test_verify_empty_password(self):
        assert verify_password("", hash_password("nonempty")) is False


class TestJWT:
    def test_access_token_decode(self):
        token = create_access_token("user-123")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-123"
        assert payload["type"] == "access"

    def test_refresh_token_decode(self):
        token = create_refresh_token("user-456")
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "user-456"
        assert payload["type"] == "refresh"

    def test_access_token_has_exp(self):
        token = create_access_token("user-789")
        payload = decode_token(token)
        assert "exp" in payload
        assert payload["exp"] > time.time()

    def test_extra_claims_in_access_token(self):
        token = create_access_token("u1", extra_claims={"role": "admin", "name": "Bob"})
        payload = decode_token(token)
        assert payload["role"] == "admin"
        assert payload["name"] == "Bob"

    def test_tampered_token_returns_none(self):
        token = create_access_token("u1")
        bad = token[:-5] + "xxxxx"
        assert decode_token(bad) is None

    def test_completely_invalid_token(self):
        assert decode_token("not.a.token") is None

    def test_empty_token(self):
        assert decode_token("") is None

    def test_access_token_rejects_refresh(self):
        """Un token de type refresh ne doit pas être accepté comme access token."""
        refresh = create_refresh_token("u1")
        payload = decode_token(refresh)
        assert payload["type"] == "refresh"
        # Le service auth vérifiera que type == "access"
        assert payload["type"] != "access"
