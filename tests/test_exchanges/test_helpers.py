# tests/test_exchanges/test_helpers.py

import pytest
from apps.exchanges.helpers import (
    is_valid_symbol,
    is_valid_amount,
    mask_sensitive_data,
    hash_data,
    generate_secure_token,
)

pytestmark = pytest.mark.django_db # نیاز نیست برای توابع کمکی که با پایگاه داده کار نمی‌کنند


class TestExchangeHelpers:
    def test_is_valid_symbol(self):
        assert is_valid_symbol("BTCUSDT") is True
        assert is_valid_symbol("ETH/USD") is True
        assert is_valid_symbol("INVALID-SYMBOL") is False
        assert is_valid_symbol("123") is False

    def test_is_valid_amount(self):
        assert is_valid_amount("1.5") is True
        assert is_valid_amount(100) is True
        assert is_valid_amount("0") is False
        assert is_valid_amount("-5") is False
        assert is_valid_amount("abc") is False

    def test_mask_sensitive_data(self):
        data = "my_secret_api_key_12345"
        masked = mask_sensitive_data(data, 5)
        assert masked == "my_ap..._12345"

    def test_hash_data(self):
        data = "sensitive_data"
        hashed = hash_data(data)
        assert isinstance(hashed, str)
        assert len(hashed) == 64 # SHA-256

    def test_generate_secure_token(self):
        token = generate_secure_token(16)
        assert isinstance(token, str)
        assert len(token) > 0
