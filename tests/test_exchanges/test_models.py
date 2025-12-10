# tests/test_exchanges/test_models.py

import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from apps.exchanges.models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    OrderHistory,
    MarketDataCandle,
)
from apps.exchanges.helpers import is_valid_symbol, is_valid_amount

pytestmark = pytest.mark.django_db


class TestExchangeModel:
    def test_create_exchange(self, ExchangeFactory):
        exchange = ExchangeFactory()
        assert exchange.name is not None
        assert exchange.code is not None
        assert exchange.is_active is True

    def test_exchange_str_representation(self, ExchangeFactory):
        exchange = ExchangeFactory(name="Test Exchange")
        assert str(exchange) == "Test Exchange"


class TestExchangeAccountModel:
    def test_create_exchange_account(self, ExchangeAccountFactory):
        account = ExchangeAccountFactory()
        assert account.user is not None
        assert account.exchange is not None
        # تأیید رمزنگاری
        assert account._api_key_encrypted is not None
        assert account._api_secret_encrypted is not None

    def test_exchange_account_str_representation(self, ExchangeAccountFactory):
        account = ExchangeAccountFactory(label="My Account", exchange__name="Binance")
        expected_str = "user@example.com - Binance (My Account)" # بسته به نحوه تعریف user در factory
        # اگر user دارای ایمیل نباشد، باید از یک user واقعی استفاده کنیم یا factory را تغییر دهیم
        # برای سادگی، فرض می‌کنیم user دارای ایمیل است
        assert account.user.email in str(account)
        assert account.exchange.name in str(account)
        assert account.label in str(account)


class TestWalletModel:
    def test_create_wallet(self, WalletFactory):
        wallet = WalletFactory()
        assert wallet.exchange_account is not None
        assert wallet.wallet_type is not None

    def test_wallet_str_representation(self, WalletFactory):
        wallet = WalletFactory(exchange_account__label="Main", wallet_type="SPOT")
        assert "Main - SPOT" in str(wallet)


class TestWalletBalanceModel:
    def test_create_wallet_balance(self, WalletBalanceFactory):
        balance = WalletBalanceFactory()
        assert balance.wallet is not None
        assert balance.asset_symbol is not None
        assert balance.total_balance >= 0

    def test_wallet_balance_str_representation(self, WalletBalanceFactory):
        balance = WalletBalanceFactory(asset_symbol="BTC", available_balance=Decimal('1.5'))
        assert "BTC" in str(balance)
        assert "1.5" in str(balance)


class TestAggregatedPortfolioModel:
    def test_create_aggregated_portfolio(self, AggregatedPortfolioFactory):
        portfolio = AggregatedPortfolioFactory()
        assert portfolio.user is not None
        assert portfolio.base_currency == "USD"

    def test_aggregated_portfolio_str_representation(self, AggregatedPortfolioFactory):
        portfolio = AggregatedPortfolioFactory(user__email="user@example.com")
        assert "user@example.com" in str(portfolio)


class TestAggregatedAssetPositionModel:
    def test_create_aggregated_asset_position(self, AggregatedAssetPositionFactory):
        position = AggregatedAssetPositionFactory()
        assert position.aggregated_portfolio is not None
        assert position.asset_symbol is not None

    def test_aggregated_asset_position_str_representation(self, AggregatedAssetPositionFactory):
        position = AggregatedAssetPositionFactory(asset_symbol="ETH", aggregated_portfolio__user__email="user@example.com")
        assert "ETH" in str(position)
        assert "user@example.com" in str(position)


class TestOrderHistoryModel:
    def test_create_order_history(self, OrderHistoryFactory):
        order = OrderHistoryFactory()
        assert order.exchange_account is not None
        assert order.order_id is not None
        assert order.status in [choice[0] for choice in OrderHistory.STATUS_CHOICES]

    def test_order_history_str_representation(self, OrderHistoryFactory):
        order = OrderHistoryFactory(symbol="BTCUSDT", side="BUY", status="FILLED")
        assert "BUY" in str(order)
        assert "BTCUSDT" in str(order)
        assert "FILLED" in str(order)


class TestMarketDataCandleModel:
    def test_create_market_data_candle(self, MarketDataCandleFactory):
        candle = MarketDataCandleFactory()
        assert candle.exchange is not None
        assert candle.symbol is not None
        assert candle.open_time is not None

    def test_market_data_candle_str_representation(self, MarketDataCandleFactory):
        candle = MarketDataCandleFactory(symbol="ETHUSDT", interval="1h", open_time=timezone.now())
        assert "ETHUSDT" in str(candle)
        assert "1h" in str(candle)

    def test_market_data_candle_unique_together(self, MarketDataCandleFactory):
        """Test that a candle with the same exchange, symbol, interval, and open_time cannot be created."""
        candle1 = MarketDataCandleFactory()
        with pytest.raises(Exception): # IntegrityError یا ValidationError
            MarketDataCandleFactory(
                exchange=candle1.exchange,
                symbol=candle1.symbol,
                interval=candle1.interval,
                open_time=candle1.open_time
            )
