# tests/test_market_data/factories.py

import factory
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
from apps.instruments.models import Instrument # فرض بر این است که وجود دارد
from apps.connectors.models import APICredential # فرض بر این است که وجود دارد

class DataSourceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = DataSource

    name = factory.Sequence(lambda n: f"DataSource_{n}")
    type = factory.Faker('random_element', elements=[choice[0] for choice in DataSource.TYPE_CHOICES])
    is_active = True
    is_sandbox = False
    rate_limit_per_minute = 1200
    base_url = factory.Faker('url')


class InstrumentFactory(factory.django.DjangoModelFactory): # اگر Instrument در تست‌های market_data نیاز باشد
    class Meta:
        model = Instrument

    symbol = factory.Sequence(lambda n: f"SYM{n:03d}")
    name = factory.Faker('word')


class MarketDataConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataConfig

    instrument = factory.SubFactory(InstrumentFactory)
    data_source = factory.SubFactory(DataSourceFactory)
    timeframe = factory.Faker('random_element', elements=['1m', '5m', '1h', '1d'])
    data_type = factory.Faker('random_element', elements=[choice[0] for choice in MarketDataConfig.DATA_TYPE_CHOICES])
    is_realtime = False
    is_historical = True
    status = factory.Faker('random_element', elements=[choice[0] for choice in MarketDataConfig.INSTRUMENT_SOURCE_STATUS_CHOICES])


class MarketDataSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataSnapshot

    config = factory.SubFactory(MarketDataConfigFactory)
    timestamp = factory.LazyFunction(timezone.now)
    open_price = factory.Faker('pydecimal', left_digits=8, right_digits=8, positive=True)
    high_price = factory.LazyAttribute(lambda obj: obj.open_price * factory.Faker('pydecimal', left_digits=1, right_digits=2, min_value=1.001, max_value=1.05))
    low_price = factory.LazyAttribute(lambda obj: obj.open_price * factory.Faker('pydecimal', left_digits=1, right_digits=2, min_value=0.95, max_value=0.999))
    close_price = factory.LazyAttribute(lambda obj: (obj.high_price + obj.low_price) / 2)
    volume = factory.Faker('pydecimal', left_digits=12, right_digits=8, positive=True)


class MarketDataOrderBookFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataOrderBook

    config = factory.SubFactory(MarketDataConfigFactory)
    timestamp = factory.LazyFunction(timezone.now)
    bids = factory.LazyFunction(lambda: [[Decimal('50000.00'), Decimal('1.0')], [Decimal('49999.99'), Decimal('0.5')]])
    asks = factory.LazyFunction(lambda: [[Decimal('50001.00'), Decimal('1.0')], [Decimal('50002.00'), Decimal('0.5')]])


class MarketDataTickFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataTick

    config = factory.SubFactory(MarketDataConfigFactory)
    timestamp = factory.LazyFunction(timezone.now)
    price = factory.Faker('pydecimal', left_digits=8, right_digits=8, positive=True)
    quantity = factory.Faker('pydecimal', left_digits=10, right_digits=8, positive=True)
    side = factory.Faker('random_element', elements=['BUY', 'SELL'])


class MarketDataSyncLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataSyncLog

    config = factory.SubFactory(MarketDataConfigFactory)
    start_time = factory.LazyFunction(timezone.now)
    end_time = factory.LazyFunction(timezone.now)
    status = factory.Faker('random_element', elements=[choice[0] for choice in MarketDataSyncLog.STATUS_CHOICES])
    records_synced = factory.Faker('pyint', min_value=0, max_value=10000)


class MarketDataCacheFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataCache

    config = factory.SubFactory(MarketDataConfigFactory)
    latest_snapshot = factory.Dict({
        "timestamp": factory.LazyFunction(lambda: int(timezone.now().timestamp())),
        "open": factory.Faker('pydecimal', left_digits=8, right_digits=8, positive=True),
        "high": factory.Faker('pydecimal', left_digits=8, right_digits=8, positive=True),
        "low": factory.Faker('pydecimal', left_digits=8, right_digits=8, positive=True),
        "close": factory.Faker('pydecimal', left_digits=8, right_digits=8, positive=True),
        "volume": factory.Faker('pydecimal', left_digits=12, right_digits=8, positive=True),
    })
