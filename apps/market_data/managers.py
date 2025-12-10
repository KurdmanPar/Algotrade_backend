# apps/market_data/managers.py

from django.db import models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import MarketDataSnapshot, MarketDataOrderBook, MarketDataTick, MarketDataConfig

class MarketDataConfigManager(models.Manager):
    """
    Custom manager for MarketDataConfig model.
    Provides methods for finding configs based on specific criteria.
    """
    def active_configs(self):
        """
        Returns configs with status 'SUBSCRIBED' or 'PENDING'.
        """
        return self.filter(status__in=['SUBSCRIBED', 'PENDING'])

    def for_instrument(self, instrument):
        """
        Returns configs related to a specific instrument.
        """
        return self.filter(instrument=instrument)

    def for_data_source(self, data_source):
        """
        Returns configs related to a specific data source.
        """
        return self.filter(data_source=data_source)

    def for_specific_timeframe(self, timeframe):
        """
        Returns configs for a specific timeframe (e.g., '1m', '1h', '1d').
        """
        return self.filter(timeframe=timeframe)

    def for_data_type(self, data_type):
        """
        Returns configs for a specific data type (e.g., 'OHLCV', 'TICK', 'ORDER_BOOK').
        """
        return self.filter(data_type=data_type)

    def requiring_historical_sync(self):
        """
        Returns configs that are marked for historical synchronization.
        """
        return self.filter(is_historical=True)

    def requiring_realtime_sync(self):
        """
        Returns configs that are marked for real-time synchronization.
        """
        return self.filter(is_realtime=True)


class MarketDataSnapshotQuerySet(models.QuerySet):
    """
    Custom QuerySet for MarketDataSnapshot model.
    Provides methods for filtering and aggregating snapshots.
    """
    def for_config(self, config):
        """
        Filters snapshots for a specific MarketDataConfig.
        """
        return self.filter(config=config)

    def for_instrument(self, instrument):
        """
        Filters snapshots for a specific instrument via its configs.
        """
        return self.filter(config__instrument=instrument)

    def in_date_range(self, start_date, end_date):
        """
        Filters snapshots within a specific date range (based on timestamp).
        """
        return self.filter(timestamp__date__gte=start_date.date(), timestamp__date__lte=end_date.date())

    def after_timestamp(self, timestamp):
        """
        Filters snapshots after a specific timestamp.
        """
        return self.filter(timestamp__gt=timestamp)

    def before_timestamp(self, timestamp):
        """
        Filters snapshots before a specific timestamp.
        """
        return self.filter(timestamp__lt=timestamp)

    def latest_n(self, n, config):
        """
        Gets the latest N snapshots for a specific config.
        """
        return self.for_config(config).order_by('-timestamp')[:n]

    def latest_for_instrument(self, instrument):
        """
        Gets the latest snapshot for a specific instrument across all its configs.
        """
        return self.for_instrument(instrument).order_by('-timestamp').first()

    def calculate_vwap(self, config, start_time, end_time):
        """
        Calculates VWAP (Volume Weighted Average Price) for a given config and time range.
        This is a simplified example; a more robust implementation might be needed for production.
        """
        snapshots = self.for_config(config).in_date_range(start_time, end_time)
        total_value = Decimal('0')
        total_volume = Decimal('0')
        for snap in snapshots:
            # قیمت میانگین (High + Low + Close) / 3 یا Close فقط
            avg_price = (snap.high_price + snap.low_price + snap.close_price) / 3
            total_value += avg_price * snap.volume
            total_volume += snap.volume

        if total_volume > 0:
            return total_value / total_volume
        else:
            return Decimal('0') # یا None یا ایجاد یک استثنا

    def calculate_periodic_ohlc(self, config, start_time, end_time, aggregation_period='1h'):
        """
        Aggregates snapshots within a time range into periodic OHLC data (e.g., 1h candles from 1m data).
        This is a more complex operation, often handled by the database engine itself (e.g., TimescaleDB).
        This method provides a basic Django ORM implementation.
        """
        # توجه: این یک پیاده‌سازی ساده است. برای حجم زیاد داده، استفاده از SQL خام یا یک پایگاه داده سری زمانی مانند TimescaleDB توصیه می‌شود.
        snapshots = self.for_config(config).filter(
            timestamp__gte=start_time,
            timestamp__lte=end_time
        ).order_by('timestamp')

        if not snapshots.exists():
            return []

        # تبدیل aggregation_period به تایم دلتا (مثلاً '1h' -> timedelta(hours=1))
        # این قسمت نیاز به یک تابع تجزیه ساده دارد
        import re
        match = re.match(r'(\d+)([smhdw])', aggregation_period)
        if not match:
            raise ValueError("Invalid aggregation period format. Use e.g., '1m', '5m', '1h', '1d'.")
        num, unit = match.groups()
        num = int(num)
        if unit == 's':
            delta = timedelta(seconds=num)
        elif unit == 'm':
            delta = timedelta(minutes=num)
        elif unit == 'h':
            delta = timedelta(hours=num)
        elif unit == 'd':
            delta = timedelta(days=num)
        elif unit == 'w':
            delta = timedelta(weeks=num)
        else:
            raise ValueError(f"Unsupported time unit: {unit}")

        # گروه‌بندی و محاسبه OHLC
        aggregated_data = []
        current_bucket_start = None
        bucket_open = None
        bucket_high = Decimal('-Infinity')
        bucket_low = Decimal('Infinity')
        bucket_close = None
        bucket_volume = Decimal('0')

        for snap in snapshots:
            bucket_start_time = snap.timestamp.replace(
                second=0, microsecond=0
            ) + timedelta(minutes=(snap.timestamp.minute // num) * num)

            if current_bucket_start is None:
                current_bucket_start = bucket_start_time
                bucket_open = snap.open_price
            elif snap.timestamp < current_bucket_start + delta:
                # داخل همان باکت
                pass
            else:
                # اتمام باکت فعلی، ذخیره و شروع باکت جدید
                if bucket_open is not None: # اگر حداقل یک داده در باکت بود
                    aggregated_data.append({
                        'timestamp': current_bucket_start,
                        'open': bucket_open,
                        'high': bucket_high,
                        'low': bucket_low,
                        'close': bucket_close,
                        'volume': bucket_volume
                    })
                current_bucket_start = bucket_start_time
                bucket_open = snap.open_price

            # بروزرسانی OHLC و حجم برای باکت فعلی
            bucket_high = max(bucket_high, snap.high_price)
            bucket_low = min(bucket_low, snap.low_price)
            bucket_close = snap.close_price # آخرین close در باکت
            bucket_volume += snap.volume

        # ذخیره آخرین باکت
        if bucket_open is not None:
             aggregated_data.append({
                 'timestamp': current_bucket_start,
                 'open': bucket_open,
                 'high': bucket_high,
                 'low': bucket_low,
                 'close': bucket_close,
                 'volume': bucket_volume
             })

        return aggregated_data


class MarketDataSnapshotManager(models.Manager):
    """
    Custom manager for MarketDataSnapshot model.
    Uses the custom QuerySet.
    """
    def get_queryset(self):
        return MarketDataSnapshotQuerySet(self.model, using=self._db)

    # می‌توانید متد‌هایی که در QuerySet تعریف نشده‌اند یا منطق خاصی دارند را اینجا اضافه کنید
    # مثلاً متدی برای ایجاد یک کندل جدید بر اساس آخرین داده و داده جدید ورودی
    # def update_or_create_candle(self, config, new_data):
    #     # منطق سفارشی برای به‌روزرسانی یا ایجاد یک کندل
    #     pass


class MarketDataOrderBookQuerySet(models.QuerySet):
    """
    Custom QuerySet for MarketDataOrderBook model.
    Provides methods for filtering order books.
    """
    def for_config(self, config):
        """
        Filters order books for a specific MarketDataConfig.
        """
        return self.filter(config=config)

    def latest_for_config(self, config):
        """
        Gets the latest order book for a specific config.
        """
        return self.for_config(config).order_by('-timestamp').first()

    def latest_n_for_config(self, config, n):
        """
        Gets the latest N order books for a specific config.
        """
        return self.for_config(config).order_by('-timestamp')[:n]

    def in_date_range(self, start_date, end_date):
        """
        Filters order books within a specific date range.
        """
        return self.filter(timestamp__date__gte=start_date.date(), timestamp__date__lte=end_date.date())


class MarketDataOrderBookManager(models.Manager):
    """
    Custom manager for MarketDataOrderBook model.
    Uses the custom QuerySet.
    """
    def get_queryset(self):
        return MarketDataOrderBookQuerySet(self.model, using=self._db)


class MarketDataTickQuerySet(models.QuerySet):
    """
    Custom QuerySet for MarketDataTick model.
    Provides methods for filtering and aggregating ticks.
    """
    def for_config(self, config):
        """
        Filters ticks for a specific MarketDataConfig.
        """
        return self.filter(config=config)

    def for_instrument(self, instrument):
        """
        Filters ticks for a specific instrument via its configs.
        """
        return self.filter(config__instrument=instrument)

    def of_side(self, side):
        """
        Filters ticks based on trade side ('BUY' or 'SELL').
        """
        return self.filter(side=side)

    def in_date_range(self, start_date, end_date):
        """
        Filters ticks within a specific date range.
        """
        return self.filter(timestamp__date__gte=start_date.date(), timestamp__date__lte=end_date.date())

    def after_timestamp(self, timestamp):
        """
        Filters ticks after a specific timestamp.
        """
        return self.filter(timestamp__gt=timestamp)

    def calculate_volume_by_side(self, config, start_time, end_time):
        """
        Calculates total volume bought and sold for a config in a time range.
        """
        ticks = self.for_config(config).in_date_range(start_time, end_time)
        buy_vol = ticks.of_side('BUY').aggregate(total=models.Sum('quantity'))['total'] or Decimal('0')
        sell_vol = ticks.of_side('SELL').aggregate(total=models.Sum('quantity'))['total'] or Decimal('0')
        return {'buy_volume': buy_vol, 'sell_volume': sell_vol}


class MarketDataTickManager(models.Manager):
    """
    Custom manager for MarketDataTick model.
    Uses the custom QuerySet.
    """
    def get_queryset(self):
        return MarketDataTickQuerySet(self.model, using=self._db)

# سایر منیجرها برای مدل‌های دیگر (مثل MarketDataSyncLog، MarketDataCache) نیز می‌توانند اضافه شوند
# مثلاً:
# class MarketDataSyncLogManager(models.Manager):
#     ...
