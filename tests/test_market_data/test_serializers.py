# tests/test_market_data/test_serializers.py

import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from apps.market_data.models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)
from apps.market_data.serializers import (
    DataSourceSerializer,
    MarketDataConfigSerializer,
    MarketDataSnapshotSerializer,
    MarketDataOrderBookSerializer,
    MarketDataTickSerializer,
    MarketDataSyncLogSerializer,
    MarketDataCacheSerializer,
)

pytestmark = pytest.mark.django_db


class TestDataSourceSerializer:
    def test_data_source_serializer_create(self, DataSourceFactory):
        data = {
            'name': 'NewSource',
            'type': 'REST_API',
            'is_active': True,
            'rate_limit_per_minute': 1000,
            'base_url': 'https://api.newsource.com',
        }
        serializer = DataSourceSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.name == 'NewSource'
        assert instance.rate_limit_per_minute == 1000

    # ... سایر تست‌های DataSourceSerializer


class TestMarketDataConfigSerializer:
    def test_market_data_config_serializer_create(self, MarketDataConfigFactory, DataSourceFactory, InstrumentFactory):
        data_source = DataSourceFactory()
        instrument = InstrumentFactory()
        data = {
            'instrument': instrument.id,
            'data_source': data_source.id,
            'timeframe': '1h',
            'data_type': 'OHLCV',
            'is_realtime': True,
            'is_historical': False,
            'status': 'PENDING',
        }
        serializer = MarketDataConfigSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.instrument == instrument
        assert instance.data_source == data_source
        assert instance.timeframe == '1h'
        assert instance.is_realtime is True

    def test_market_data_config_serializer_validate_timeframe_for_data_type(self, MarketDataConfigFactory, DataSourceFactory, InstrumentFactory):
        data_source = DataSourceFactory()
        instrument = InstrumentFactory()
        # تلاش برای ایجاد TICK با timeframe بلند
        data = {
            'instrument': instrument.id,
            'data_source': data_source.id,
            'timeframe': '1d',
            'data_type': 'TICK', # TICK نباید با 1d
            'is_realtime': True,
            'is_historical': False,
            'status': 'PENDING',
        }
        serializer = MarketDataConfigSerializer(data=data)
        assert not serializer.is_valid()
        assert "data_type" in serializer.errors # یا "non_field_errors" بسته به پیاده‌سازی


    # ... سایر تست‌های MarketDataConfigSerializer


class TestMarketDataSnapshotSerializer:
    def test_market_data_snapshot_serializer_create(self, MarketDataSnapshotFactory, MarketDataConfigFactory):
        config = MarketDataConfigFactory()
        data = {
            'config': config.id,
            'timestamp': timezone.now(),
            'open_price': '50000.00000000',
            'high_price': '50100.00000000',
            'low_price': '49900.00000000',
            'close_price': '50050.00000000',
            'volume': '10.50000000',
        }
        serializer = MarketDataSnapshotSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.config == config
        assert instance.open_price == Decimal('50000.00000000')

    def test_market_data_snapshot_serializer_validate_ohlcv_logic(self, MarketDataConfigFactory):
        config = MarketDataConfigFactory()
        data = {
            'config': config.id,
            'timestamp': timezone.now(),
            'open_price': '50000.00000000',
            'high_price': '49900.00000000', # اشتباه: High < Open
            'low_price': '49950.00000000',
            'close_price': '50050.00000000',
            'volume': '10.50000000',
        }
        serializer = MarketDataSnapshotSerializer(data=data)
        assert not serializer.is_valid()
        assert "non_field_errors" in serializer.errors # یا فیلد خاص


    # ... سایر تست‌های MarketDataSnapshotSerializer

# سایر فایل‌های تست (test_views.py, test_permissions.py, test_services.py, test_tasks.py, test_helpers.py, test_exceptions.py, test_managers.py) نیز به همین ترتیب ایجاد یا ارتقا می‌شوند.

# مثال کوتاه برای test_helpers.py:
# tests/test_market_data/test_helpers.py
# import pytest
# from apps.market_data.helpers import normalize_data_from_source, validate_ohlcv_data
#
# def test_normalize_data_from_source():
#     raw_data = {...} # یک نمونه داده خام
#     normalized = normalize_data_from_source(raw_data, 'BINANCE', 'OHLCV')
#     assert normalized is not None
#     assert 'timestamp' in normalized
#     # ... اعتبارسنجی ساختار نرمالایز شده
#
# def test_validate_ohlcv_data():
#     valid_data = {'timestamp': 1234567890, 'open': '50000', 'high': '50100', 'low': '49900', 'close': '50050', 'volume': '10'}
#     validated = validate_ohlcv_data(valid_data)
#     assert validated == valid_data
#
#     invalid_data = {'open': '50000', 'high': '49900'} # High < Open
#     validated = validate_ohlcv_data(invalid_data)
#     assert validated is None # یا یک ValidationError رخ دهد

# مثال کوتاه برای test_exceptions.py:
# tests/test_market_data/test_exceptions.py
# import pytest
# from apps.market_data.exceptions import DataSyncError, DataFetchError
#
# def test_data_sync_error():
#     with pytest.raises(DataSyncError):
#         raise DataSyncError("Test sync error")
#
# def test_data_fetch_error():
#     with pytest.raises(DataFetchError):
#         raise DataFetchError("Test fetch error")

# و به همین ترتیب برای بقیه...
