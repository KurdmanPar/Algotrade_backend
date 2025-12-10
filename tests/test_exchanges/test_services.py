# tests/test_exchanges/test_services.py

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from apps.exchanges.models import ExchangeAccount, Wallet, WalletBalance, OrderHistory
from apps.exchanges.services import ExchangeService
from apps.exchanges.exceptions import ExchangeSyncError, OrderExecutionError
from apps.connectors.service import ConnectorService # فرض بر این است که وجود دارد

pytestmark = pytest.mark.django_db


class TestExchangeService:
    @patch('apps.exchanges.services.ConnectorService') # فرض بر این است که ConnectorService وجود دارد
    @patch('apps.exchanges.services.MarketDataService')
    def test_sync_exchange_account_success(self, MockMarketDataService, MockConnectorService, ExchangeAccountFactory):
        # Mock کردن ConnectorService
        mock_connector_instance = MockConnectorService.return_value
        mock_connector_instance.get_account_info.return_value = {'permissions': {'trade': True}}
        mock_connector_instance.get_account_balances.return_value = [{'asset': 'BTC', 'total': '1.0', 'available': '0.9'}]
        mock_connector_instance.get_account_orders.return_value = []

        account = ExchangeAccountFactory()

        service = ExchangeService()
        result = service.sync_exchange_account(account)

        assert result['sync_time'] is not None
        # بررسی اینکه موجودی ایجاد شده است
        wallet = Wallet.objects.get(exchange_account=account, wallet_type='SPOT')
        balance = WalletBalance.objects.get(wallet=wallet, asset_symbol='BTC')
        assert balance.available_balance == Decimal('0.9')

    @patch('apps.exchanges.services.ConnectorService')
    def test_place_order_success(self, MockConnectorService, ExchangeAccountFactory, TradingBotFactory): # فرض بر این است که TradingBotFactory وجود دارد
        mock_connector_instance = MockConnectorService.return_value
        mock_connector_instance.place_order.return_value = {
            'id': 'ORDER123',
            'symbol': 'BTCUSDT',
            'side': 'BUY',
            'type': 'LIMIT',
            'status': 'NEW',
            'price': '50000',
            'amount': '0.1',
            'timestamp': 1234567890000
        }

        account = ExchangeAccountFactory()
        bot = TradingBotFactory(owner=account.user) # فرض بر این است که TradingBot دارای owner است
        order_params = {
            'symbol': 'BTCUSDT',
            'side': 'buy',
            'type': 'limit',
            'amount': '0.1',
            'price': '50000'
        }

        service = ExchangeService()
        response = service.place_order(account, bot, order_params)

        assert response['id'] == 'ORDER123'
        # بررسی اینکه رکورد تاریخچه سفارش ایجاد شده است
        order_history = OrderHistory.objects.get(order_id='ORDER123')
        assert order_history.trading_bot == bot

    # سایر تست‌های سرویس...
