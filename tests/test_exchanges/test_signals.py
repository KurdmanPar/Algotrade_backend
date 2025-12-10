# tests/test_exchanges/test_signals.py

import pytest
from django.db.models.signals import post_save
from django.test import TestCase
from unittest.mock import patch
from apps.exchanges.models import ExchangeAccount, OrderHistory, MarketDataCandle
from apps.exchanges import signals # اطمینان از وارد شدن سیگنال‌ها

pytestmark = pytest.mark.django_db


class TestExchangeSignals(TestCase):
    def test_handle_exchange_account_save_creates_default_wallet(self):
        account = ExchangeAccount.objects.create(
            user_id=1, # یا از یک فکتوری استفاده کنید
            exchange_id=1, # یا از یک فکتوری استفاده کنید
            label="Test Account",
            _api_key_encrypted="dummy",
            _api_secret_encrypted="dummy",
        )

        # چک کردن اینکه یک کیف پول SPOT پیش‌فرض ایجاد شده است
        default_wallet = Wallet.objects.filter(
            exchange_account=account,
            wallet_type='SPOT',
            is_default=True
        ).first()

        assert default_wallet is not None

    # سایر تست‌های سیگنال مانند post_save برای OrderHistory یا MarketDataCandle
    # بسته به پیچیدگی منطق سیگنال می‌توانید تست کنید.
    # مثلاً بررسی اینکه آیا یک تاسک پس از ذخیره رکورد فعال می‌شود یا خیر.
    # این نیازمند mock کردن تاسک یا بررسی اثرات جانبی است.
