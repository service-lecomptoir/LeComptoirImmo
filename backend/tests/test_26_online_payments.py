"""Tests unitaires du paiement en ligne (config gestionnaire, chiffrement,
signature webhook) — sans DB ni appel réseau."""
import hashlib
import hmac

import pytest

from app.core.crypto import decrypt_secret, encrypt_secret
from app.core.exceptions import BadRequestException
from app.models.user import User
from app.services import online_payment_service as ops


def test_crypto_roundtrip_and_empty():
    assert decrypt_secret(encrypt_secret("sk_live_secret")) == "sk_live_secret"
    assert encrypt_secret("") is None
    assert encrypt_secret(None) is None
    assert decrypt_secret(None) is None
    assert decrypt_secret("not-a-token") is None


def test_apply_config_encrypts_secret_and_masks_output():
    u = User()
    ops.apply_config(u, {
        "payment_provider": "stripe",
        "stripe_secret_key": "sk_test_123",
        "stripe_publishable_key": "pk_test_1",
        "payment_currency": "usd",
        "card_payments_enabled": True,
    })
    assert u.payment_provider == "stripe"
    assert u.payment_currency == "USD"
    assert u.stripe_secret_key_enc and u.stripe_secret_key_enc != "sk_test_123"
    assert decrypt_secret(u.stripe_secret_key_enc) == "sk_test_123"
    out = ops.config_out(u)
    assert out["stripe"]["secret_key_set"] is True
    assert out["payment_currency"] == "USD"
    # Le secret n'apparaît jamais en clair dans la sortie.
    assert "sk_test_123" not in str(out)


def test_enable_without_keys_is_rejected():
    u = User()
    with pytest.raises(BadRequestException):
        ops.apply_config(u, {"payment_provider": "stripe", "card_payments_enabled": True})
    v = User()
    with pytest.raises(BadRequestException):
        ops.apply_config(v, {"payment_provider": "sumup", "card_payments_enabled": True,
                             "sumup_merchant_code": "M1"})  # clé API manquante


def test_blank_secret_keeps_existing_clear_marker_removes():
    u = User()
    ops.apply_config(u, {"payment_provider": "stripe", "stripe_secret_key": "sk_a"})
    enc = u.stripe_secret_key_enc
    # Pas de secret fourni → on conserve l'existant.
    ops.apply_config(u, {"stripe_publishable_key": "pk_x"})
    assert u.stripe_secret_key_enc == enc
    # Marqueur explicite → on efface.
    ops.apply_config(u, {"stripe_secret_key": "__clear__"})
    assert u.stripe_secret_key_enc is None


def test_invalid_provider_rejected():
    u = User()
    with pytest.raises(BadRequestException):
        ops.apply_config(u, {"payment_provider": "paypal"})


def test_verify_stripe_signature():
    payload = b'{"id":"evt_1"}'
    secret = "whsec_test"
    t = "1700000000"
    good = hmac.new(secret.encode(), t.encode() + b"." + payload, hashlib.sha256).hexdigest()
    assert ops._verify_stripe_signature(payload, f"t={t},v1={good}", secret) is True
    assert ops._verify_stripe_signature(payload, f"t={t},v1=deadbeef", secret) is False
    assert ops._verify_stripe_signature(payload, "garbage", secret) is False
