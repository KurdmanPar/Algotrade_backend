# tests/test_exchanges/test_serializers.py

import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from apps.exchanges.models import ExchangeAccount, Wallet, OrderHistory
from apps.exchanges.serializers import (
    ExchangeAccountSerializer,
    WalletSerializer,
    OrderHistorySerializer,
    # سایر سریالایزرها
)
from apps.bots.models import TradingBot # فرض بر این است که مدل وجود دارد

pytestmark = pytest.mark.django_db


class TestExchangeAccountSerializer:
    def test_exchange_account_serializer_create(self, ExchangeAccountFactory, ExchangeFactory):
        exchange = ExchangeFactory()
        user = ExchangeAccountFactory().user # ایجاد یک کاربر
        api_key = 'new_api_key_123'
        api_secret = 'new_api_secret_456'

        data = {
            'exchange': exchange.id,
            'label': 'New Account',
            'api_key': api_key,
            'api_secret': api_secret,
            'is_active': True,
        }

        serializer = ExchangeAccountSerializer(data=data, context={'request': type('MockRequest', (), {'user': user})()})
        assert serializer.is_valid(), serializer.errors
        account = serializer.save()

        assert account.label == 'New Account'
        assert account.api_key == api_key # فرض بر این است که property یا setter به درستی کار می‌کند
        assert account.api_secret == api_secret
        assert account.user == user

    def test_exchange_account_serializer_update(self, ExchangeAccountFactory):
        account = ExchangeAccountFactory()
        new_label = 'Updated Label'
        new_api_key = 'updated_api_key_789'
        new_api_secret = 'updated_api_secret_012'

        data = {
            'label': new_label,
            'api_key': new_api_key,
            'api_secret': new_api_secret,
        }

        serializer = ExchangeAccountSerializer(instance=account, data=data, partial=True)
        assert serializer.is_valid()
        updated_account = serializer.save()

        assert updated_account.label == new_label
        assert updated_account.api_key == new_api_key
        assert updated_account.api_secret == new_api_secret


class TestWalletSerializer:
    def test_wallet_serializer_create(self, WalletFactory):
        data = {
            'exchange_account': WalletFactory.build().exchange_account.id, # استفاده از build برای ساخت شی بدون ذخیره
            'wallet_type': 'SPOT',
            'description': 'Test Spot Wallet',
            'is_default': True,
        }

        serializer = WalletSerializer(data=data)
        assert serializer.is_valid()
        wallet = serializer.save()

        assert wallet.wallet_type == 'SPOT'
        assert wallet.description == 'Test Spot Wallet'
        assert wallet.is_default is True


class TestOrderHistorySerializer:
    def test_order_history_serializer_create(self, OrderHistoryFactory):
        data = {
            'exchange_account': OrderHistoryFactory.build().exchange_account.id,
            'order_id': 'TEST_ORDER_123',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'order_type': 'LIMIT',
            'status': 'NEW',
            'price': '50000.00',
            'quantity': '0.1',
            'time_placed': timezone.now(),
            'time_updated': timezone.now(),
        }

        serializer = OrderHistorySerializer(data=data)
        assert serializer.is_valid()
        order = serializer.save()

        assert order.symbol == 'BTCUSDT'
        assert order.side == 'BUY'
        assert order.status == 'NEW'
        assert order.price == Decimal('50000.00')
        assert order.quantity == Decimal('0.1')

    # سایر تست‌های سریالایزرها...
