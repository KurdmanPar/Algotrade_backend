# tests/test_market_data/test_models.py

import pytest
from django.utils import timezone
from decimal import Decimal
from apps.market_data.models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)

pytestmark = pytest.mark.django_db


class TestDataSourceModel:
    def test_create_data_source(self, DataSourceFactory):
        ds = DataSourceFactory()
        assert ds.name is not None
        assert ds.type in [choice[0] for choice in DataSource.TYPE_CHOICES]
        assert ds.is_active is True

    def test_data_source_str_representation(self, DataSourceFactory):
        ds = DataSourceFactory(name="TestSource")
        assert str(ds) == "TestSource"


class TestMarketDataConfigModel:
    def test_create_market_data_config(self, MarketDataConfigFactory):
        config = MarketDataConfigFactory()
        assert config.instrument is not None
        assert config.data_source is not None
        assert config.timeframe is not None
        assert config.data_type in [choice[0] for choice in MarketDataConfig.DATA_TYPE_CHOICES]

    def test_market_data_config_str_representation(self, MarketDataConfigFactory):
        config = MarketDataConfigFactory(instrument__symbol="BTCUSDT", data_source__name="Binance", timeframe="1m")
        expected_str = "BTCUSDT (1m) from Binance"
        assert str(config) == expected_str

    def test_unique_together_constraint(self, MarketDataConfigFactory):
        config1 = MarketDataConfigFactory()
        with pytest.raises(Exception): # IntegrityError
            MarketDataConfigFactory(
                instrument=config1.instrument,
                data_source=config1.data_source,
                timeframe=config1.timeframe,
                data_type=config1.data_type
            )


class TestMarketDataSnapshotModel:
    def test_create_market_data_snapshot(self, MarketDataSnapshotFactory):
        snap = MarketDataSnapshotFactory()
        assert snap.config is not None
        assert snap.timestamp is not None
        assert snap.open_price >= 0
        assert snap.high_price >= snap.open_price
        assert snap.low_price <= snap.open_price
        assert snap.close_price >= snap.low_price
        assert snap.close_price <= snap.high_price
        assert snap.volume >= 0

    def test_market_data_snapshot_str_representation(self, MarketDataSnapshotFactory):
        snap = MarketDataSnapshotFactory(config__instrument__symbol="ETHUSDT", close_price=Decimal('3000.00'))
        assert "ETHUSDT" in str(snap)
        assert "C:3000.00" in str(snap)


class TestMarketDataOrderBookModel:
    def test_create_market_data_order_book(self, MarketDataOrderBookFactory):
        book = MarketDataOrderBookFactory()
        assert book.config is not None
        assert book.timestamp is not None
        assert isinstance(book.bids, list)
        assert isinstance(book.asks, list)

    def test_market_data_order_book_str_representation(self, MarketDataOrderBookFactory):
        book = MarketDataOrderBookFactory(config__instrument__symbol="ADAUSDT")
        assert "ADAUSDT" in str(book)


class TestMarketDataTickModel:
    def test_create_market_data_tick(self, MarketDataTickFactory):
        tick = MarketDataTickFactory()
        assert tick.config is not None
        assert tick.timestamp is not None
        assert tick.price >= 0
        assert tick.quantity >= 0
        assert tick.side in ['BUY', 'SELL']

    def test_market_data_tick_str_representation(self, MarketDataTickFactory):
        tick = MarketDataTickFactory(config__instrument__symbol="XRPUSDT", price=Decimal('0.50'), quantity=Decimal('100'))
        assert "Tick:" in str(tick)
        assert "XRPUSDT" in str(tick)


class TestMarketDataSyncLogModel:
    def test_create_market_data_sync_log(self, MarketDataSyncLogFactory):
        log = MarketDataSyncLogFactory()
        assert log.config is not None
        assert log.start_time is not None
        assert log.end_time is not None
        assert log.status in [choice[0] for choice in MarketDataSyncLog.STATUS_CHOICES]
        assert log.records_synced >= 0

    def test_market_data_sync_log_str_representation(self, MarketDataSyncLogFactory):
        log = MarketDataSyncLogFactory(config__instrument__symbol="LTCUSDT", status="SUCCESS")
        assert "LTCUSDT" in str(log)
        assert "SUCCESS" in str(log)


class TestMarketDataCacheModel:
    def test_create_market_data_cache(self, MarketDataCacheFactory):
        cache = MarketDataCacheFactory()
        assert cache.config is not None
        assert cache.latest_snapshot is not None
        assert isinstance(cache.latest_snapshot, dict)

    def test_market_data_cache_str_representation(self, MarketDataCacheFactory):
        cache = MarketDataCacheFactory(config__instrument__symbol="DOTUSDT")
        assert "Cache for" in str(cache)
        assert "DOTUSDT" in str(cache)
