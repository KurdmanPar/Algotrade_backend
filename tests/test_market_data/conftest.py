# tests/test_market_data/conftest.py

import pytest
from pytest_factoryboy import register
from .factories import (
    DataSourceFactory,
    MarketDataConfigFactory,
    MarketDataSnapshotFactory,
    MarketDataOrderBookFactory,
    MarketDataTickFactory,
    MarketDataSyncLogFactory,
    MarketDataCacheFactory,
)

# ثبت Factoryها به عنوان Fixture
register(DataSourceFactory)
register(MarketDataConfigFactory)
register(MarketDataSnapshotFactory)
register(MarketDataOrderBookFactory)
register(MarketDataTickFactory)
register(MarketDataSyncLogFactory)
register(MarketDataCacheFactory)

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    اطمینان از دسترسی به پایگاه داده برای تمام تست‌ها.
    """
    pass

