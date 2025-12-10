# tests/test_exchanges/test_exceptions.py

import pytest
from rest_framework.exceptions import APIException
from apps.exchanges.exceptions import (
    ExchangeBaseError,
    InvalidCredentialsError,
    ExchangeSyncError,
    OrderExecutionError,
    InsufficientBalanceError,
    # سایر استثناها
)

pytestmark = pytest.mark.django_db # نیاز نیست برای استثناها


class TestExchangeExceptions:
    def test_exchange_base_error(self):
        exc = ExchangeBaseError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 500

    def test_invalid_credentials_error(self):
        exc = InvalidCredentialsError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 401

    def test_exchange_sync_error(self):
        exc = ExchangeSyncError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 400

    def test_order_execution_error(self):
        exc = OrderExecutionError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 400

    def test_insufficient_balance_error(self):
        exc = InsufficientBalanceError()
        assert isinstance(exc, APIException)
        assert exc.status_code == 400

    # سایر تست‌های استثناها...
