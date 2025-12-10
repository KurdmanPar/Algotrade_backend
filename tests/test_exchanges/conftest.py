# tests/test_exchanges/conftest.py

import pytest
from pytest_factoryboy import register
from .factories import (
    ExchangeFactory,
    ExchangeAccountFactory,
    WalletFactory,
    WalletBalanceFactory,
    AggregatedPortfolioFactory,
    AggregatedAssetPositionFactory,
    OrderHistoryFactory,
    MarketDataCandleFactory,
)

# ثبت Factoryها به عنوان Fixture
register(ExchangeFactory)
register(ExchangeAccountFactory)
register(WalletFactory)
register(WalletBalanceFactory)
register(AggregatedPortfolioFactory)
register(AggregatedAssetPositionFactory)
register(OrderHistoryFactory)
register(MarketDataCandleFactory)

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    اطمینان از دسترسی به پایگاه داده برای تمام تست‌ها.
    """
    pass