# tests/test_exchanges/test_managers.py

import pytest
from decimal import Decimal
from apps.exchanges.models import (
    ExchangeAccount,
    Wallet,
    WalletBalance,
    OrderHistory,
    MarketDataCandle,
)
from apps.exchanges.managers import (
    ExchangeAccountManager,
    WalletManager,
    WalletBalanceManager,
    OrderHistoryManager,
    MarketDataCandleManager,
)

pytestmark = pytest.mark.django_db


class TestExchangeAccountManager:
    def test_active_manager(self, ExchangeAccountFactory):
        active_acc = ExchangeAccountFactory(is_active=True)
        inactive_acc = ExchangeAccountFactory(is_active=False)

        active_accounts = ExchangeAccount.objects.active()
        assert active_acc in active_accounts
        assert inactive_acc not in active_accounts

    def test_for_user_manager(self, ExchangeAccountFactory, CustomUserFactory):
        user1 = CustomUserFactory()
        user2 = CustomUserFactory()
        acc1 = ExchangeAccountFactory(user=user1)
        acc2 = ExchangeAccountFactory(user=user2)

        user1_accounts = ExchangeAccount.objects.for_user(user1)
        assert acc1 in user1_accounts
        assert acc2 not in user1_accounts


class TestWalletManager:
    def test_for_account_manager(self, WalletFactory):
        account = WalletFactory().exchange_account
        wallet1 = WalletFactory(exchange_account=account)
        wallet2 = WalletFactory() # حساب دیگر

        account_wallets = Wallet.objects.for_account(account)
        assert wallet1 in account_wallets
        assert wallet2 not in account_wallets


class TestWalletBalanceManager:
    def test_for_wallet_manager(self, WalletBalanceFactory):
        wallet = WalletBalanceFactory().wallet
        balance1 = WalletBalanceFactory(wallet=wallet)
        balance2 = WalletBalanceFactory() # کیف پول دیگر

        wallet_balances = WalletBalance.objects.for_wallet(wallet)
        assert balance1 in wallet_balances
        assert balance2 not in wallet_balances

    def test_with_available_balance_gt_manager(self, WalletBalanceFactory):
        balance_high = WalletBalanceFactory(available_balance=Decimal('100'))
        balance_low = WalletBalanceFactory(available_balance=Decimal('10'))

        balances_gt_50 = WalletBalance.objects.with_available_balance_gt(Decimal('50'))
        assert balance_high in balances_gt_50
        assert balance_low not in balances_gt_50


class TestOrderHistoryManager:
    def test_for_account_manager(self, OrderHistoryFactory):
        account = OrderHistoryFactory().exchange_account
        order1 = OrderHistoryFactory(exchange_account=account)
        order2 = OrderHistoryFactory() # حساب دیگر

        account_orders = OrderHistory.objects.for_account(account)
        assert order1 in account_orders
        assert order2 not in account_orders


class TestMarketDataCandleManager:
    def test_for_symbol_manager(self, MarketDataCandleFactory):
        candle_btc = MarketDataCandleFactory(symbol='BTCUSDT')
        candle_eth = MarketDataCandleFactory(symbol='ETHUSDT')

        btc_candles = MarketDataCandle.objects.for_symbol('BTCUSDT')
        assert candle_btc in btc_candles
        assert candle_eth not in btc_candles

    def test_latest_for_symbol_manager(self, MarketDataCandleFactory):
        now = timezone.now()
        old_candle = MarketDataCandleFactory(symbol='LTCUSDT', open_time=now - timedelta(hours=1))
        new_candle = MarketDataCandleFactory(symbol='LTCUSDT', open_time=now)

        latest = MarketDataCandle.objects.latest_for_symbol('LTCUSDT')
        assert latest == new_candle
