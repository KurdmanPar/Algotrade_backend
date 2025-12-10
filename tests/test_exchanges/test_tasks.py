# tests/test_exchanges/test_tasks.py

import pytest
from unittest.mock import patch
from django.core import mail
from apps.exchanges.models import ExchangeAccount, OrderHistory
from apps.exchanges.tasks import (
    sync_exchange_account_task,
    fetch_market_data_candles_task,
    place_order_task,
)

pytestmark = pytest.mark.django_db


class TestExchangeTasks:
    @patch('apps.exchanges.tasks.ExchangeService')
    def test_sync_exchange_account_task(self, MockExchangeService, ExchangeAccountFactory):
        mock_service_instance = MockExchangeService.return_value
        mock_service_instance.sync_exchange_account.return_value = {'sync_time': timezone.now()}

        account = ExchangeAccountFactory()
        result = sync_exchange_account_task(account.id)

        mock_service_instance.sync_exchange_account.assert_called_once_with(account)
        assert result is not None

    @patch('apps.exchanges.tasks.ExchangeService')
    def test_place_order_task(self, MockExchangeService, ExchangeAccountFactory, TradingBotFactory):
        mock_service_instance = MockExchangeService.return_value
        mock_service_instance.place_order.return_value = {'id': 'TASK_ORDER_123'}

        account = ExchangeAccountFactory()
        bot = TradingBotFactory(owner=account.user)
        order_params = {'symbol': 'ETHUSDT', 'side': 'buy', 'amount': '1', 'price': '3000'}

        result = place_order_task(account.id, bot.id, order_params)

        mock_service_instance.place_order.assert_called_once_with(account, bot, order_params)
        assert result['id'] == 'TASK_ORDER_123'

    # سایر تست‌های تاسک...
