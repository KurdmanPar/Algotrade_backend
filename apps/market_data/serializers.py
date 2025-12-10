# apps/market_data/serializers.py

from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from decimal import Decimal, InvalidOperation
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)

# --- سریالایزر DataSource ---
class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = '__all__'

    def validate_rate_limit_per_minute(self, value):
        """
        اعتبارسنجی حداقل نرخ مجاز.
        """
        if value < 1:
            raise serializers.ValidationError("Rate limit per minute must be at least 1.")
        return value

    def validate_supported_timeframes(self, value):
        """
        اعتبارسنجی ساختار JSON فیلد supported_timeframes (اختیاری).
        مثلاً بررسی اینکه فقط رشته‌های معتبر باشند.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Supported timeframes must be a list.")
        for tf in value:
            if not isinstance(tf, str):
                raise serializers.ValidationError("Each timeframe must be a string.")
        return value

    def validate_supported_data_types(self, value):
        """
        اعتبارسنجی ساختار JSON فیلد supported_data_types (اختیاری).
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Supported data types must be a list.")
        valid_choices = [choice[0] for choice in MarketDataConfig.DATA_TYPE_CHOICES] # از مدل MarketDataConfig استفاده می‌کنیم
        for dt in value:
            if not isinstance(dt, str) or dt not in valid_choices:
                raise serializers.ValidationError(f"Each data type must be a string and one of: {valid_choices}")
        return value

# --- سریالایزر MarketDataConfig ---
class MarketDataConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataConfig
        fields = '__all__'

    def validate(self, attrs):
        """
        اعتبارسنجی‌های سفارشی برای کانفیگ داده.
        مثلاً بررسی اینکه آیا timeframe مناسب برای data_type است یا خیر.
        """
        timeframe = attrs.get('timeframe')
        data_type = attrs.get('data_type')

        # مثال: TICK داده نباید با timeframe بلند مانند 1d تعریف شود
        if data_type == 'TICK' and timeframe in ['1d', '1w', '1M']:
            raise serializers.ValidationError("TICK data type is not suitable for long timeframes like 1d, 1w, 1M.")

        # مثال: OHLCV فقط برای timeframeهای مشخص مجاز باشد
        valid_ohlcv_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        if data_type == 'OHLCV' and timeframe not in valid_ohlcv_timeframes:
            raise serializers.ValidationError(f"Timeframe '{timeframe}' is not valid for OHLCV data type. Valid options are: {', '.join(valid_ohlcv_timeframes)}")

        # مثال: ORDER_BOOK ممکن است فقط برای timeframe 'tick' یا 'realtime' مناسب باشد
        if data_type == 'ORDER_BOOK' and timeframe != 'REALTIME':
             # یا مثلاً فقط از timeframes بسیار کوتاه پشتیبانی کند
             valid_ob_timeframes = ['TICK', 'REALTIME', '1s', '100ms'] # مثال
             if timeframe not in valid_ob_timeframes:
                 raise serializers.ValidationError(f"Timeframe '{timeframe}' is not valid for ORDER_BOOK data type. Valid options are: {', '.join(valid_ob_timeframes)}")

        # اطمینان از اینکه حداقل یکی از is_realtime یا is_historical فعال باشد
        is_realtime = attrs.get('is_realtime', self.instance.is_realtime if self.instance else False)
        is_historical = attrs.get('is_historical', self.instance.is_historical if self.instance else True)
        if not is_realtime and not is_historical:
            raise serializers.ValidationError("At least one of 'is_realtime' or 'is_historical' must be True.")

        return attrs

    def validate_depth_levels(self, value):
        """
        اعتبارسنجی تعداد سطوح عمیق سفارش.
        """
        if value is not None and (value < 1 or value > 500):
            raise serializers.ValidationError("Depth levels must be between 1 and 500.")
        return value

# --- سریالایزر MarketDataSnapshot ---
class MarketDataSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataSnapshot
        fields = '__all__'
        # اضافه کردن validators برای فیلدهای عددی
        extra_kwargs = {
            'open_price': {'validators': [MinValueValidator(Decimal('0'))]},
            'high_price': {'validators': [MinValueValidator(Decimal('0'))]},
            'low_price': {'validators': [MinValueValidator(Decimal('0'))]},
            'close_price': {'validators': [MinValueValidator(Decimal('0'))]},
            'volume': {'validators': [MinValueValidator(Decimal('0'))]},
            'best_bid': {'validators': [MinValueValidator(Decimal('0'))]},
            'best_ask': {'validators': [MinValueValidator(Decimal('0'))]},
            'bid_size': {'validators': [MinValueValidator(Decimal('0'))]},
            'ask_size': {'validators': [MinValueValidator(Decimal('0'))]},
            'quote_volume': {'validators': [MinValueValidator(Decimal('0'))]},
            'taker_buy_base_asset_volume': {'validators': [MinValueValidator(Decimal('0'))]},
            'taker_buy_quote_asset_volume': {'validators': [MinValueValidator(Decimal('0'))]},
        }

    def validate(self, attrs):
        """
        اعتبارسنجی سفارشی برای اطمینان از صحت داده OHLCV.
        مثلاً: Low <= Open <= High و Low <= Close <= High
        """
        open_price = attrs.get('open_price')
        high_price = attrs.get('high_price')
        low_price = attrs.get('low_price')
        close_price = attrs.get('close_price')

        if open_price is not None and high_price is not None and open_price > high_price:
            raise serializers.ValidationError("Open price cannot be higher than High price.")
        if open_price is not None and low_price is not None and open_price < low_price:
            raise serializers.ValidationError("Open price cannot be lower than Low price.")
        if close_price is not None and high_price is not None and close_price > high_price:
            raise serializers.ValidationError("Close price cannot be higher than High price.")
        if close_price is not None and low_price is not None and close_price < low_price:
            raise serializers.ValidationError("Close price cannot be lower than Low price.")
        if high_price is not None and low_price is not None and high_price < low_price:
            raise serializers.ValidationError("High price cannot be lower than Low price.")

        # اطمینان از اینکه timestamp منطقی است (مثلاً در گذشته نباشد، مگر اینکه داده تاریخی باشد)
        # این بستگی به نیاز سیستم دارد. برای مثال، فقط بررسی می‌کنیم که null نباشد.
        if attrs.get('timestamp') is None:
            raise serializers.ValidationError("Timestamp is required.")

        return attrs

# --- سریالایزر MarketDataOrderBook ---
class MarketDataOrderBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataOrderBook
        fields = '__all__'

    def validate_bids(self, value):
        """
        اعتبارسنجی ساختار داده bids.
        مثلاً بررسی اینکه یک لیست از لیست‌های [قیمت، مقدار] باشد و اعداد مثبت باشند.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Bids must be a list.")
        for bid_entry in value:
            if not isinstance(bid_entry, list) or len(bid_entry) != 2:
                raise serializers.ValidationError("Each bid entry must be a list of [price, quantity].")
            try:
                price = Decimal(bid_entry[0])
                qty = Decimal(bid_entry[1])
                if price <= 0 or qty <= 0:
                    raise serializers.ValidationError("Bid price and quantity must be positive.")
            except (InvalidOperation, TypeError):
                raise serializers.ValidationError("Bid price and quantity must be valid numbers.")
        return value

    def validate_asks(self, value):
        """
        اعتبارسنجی ساختار داده asks.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Asks must be a list.")
        for ask_entry in value:
            if not isinstance(ask_entry, list) or len(ask_entry) != 2:
                raise serializers.ValidationError("Each ask entry must be a list of [price, quantity].")
            try:
                price = Decimal(ask_entry[0])
                qty = Decimal(ask_entry[1])
                if price <= 0 or qty <= 0:
                    raise serializers.ValidationError("Ask price and quantity must be positive.")
            except (InvalidOperation, TypeError):
                raise serializers.ValidationError("Ask price and quantity must be valid numbers.")
        return value

    def validate(self, attrs):
        """
        اعتبارسنجی‌های سفارشی مانند بررسی ترتیب قیمت‌ها در bids و asks.
        """
        bids = attrs.get('bids', [])
        asks = attrs.get('asks', [])

        # بررسی ترتیب bids (باید نزولی باشد)
        for i in range(len(bids) - 1):
            if Decimal(bids[i][0]) < Decimal(bids[i+1][0]): # قیمت باید نزولی باشد
                raise serializers.ValidationError("Bids must be sorted in descending order by price.")

        # بررسی ترتیب asks (باید صعودی باشد)
        for i in range(len(asks) - 1):
            if Decimal(asks[i][0]) > Decimal(asks[i+1][0]): # قیمت باید صعودی باشد
                raise serializers.ValidationError("Asks must be sorted in ascending order by price.")

        # بررسی اینکه بهترین پیشنهاد فروش بیشتر از بهترین پیشنهاد خرید باشد
        if bids and asks:
            best_bid_price = Decimal(bids[0][0])
            best_ask_price = Decimal(asks[0][0])
            if best_bid_price >= best_ask_price:
                raise serializers.ValidationError("Best bid price must be less than best ask price.")

        if attrs.get('timestamp') is None:
            raise serializers.ValidationError("Timestamp is required.")

        return attrs

# --- سریالایزر MarketDataTick ---
class MarketDataTickSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataTick
        fields = '__all__'
        extra_kwargs = {
            'price': {'validators': [MinValueValidator(Decimal('0'))]},
            'quantity': {'validators': [MinValueValidator(Decimal('0'))]},
        }

    def validate(self, attrs):
        """
        اعتبارسنجی سفارشی برای تیک.
        """
        if attrs.get('timestamp') is None:
            raise serializers.ValidationError("Timestamp is required.")
        if attrs.get('side') not in ['BUY', 'SELL']:
            raise serializers.ValidationError("Side must be 'BUY' or 'SELL'.")
        return attrs

# --- سریالایزر MarketDataSyncLog ---
class MarketDataSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataSyncLog
        fields = '__all__'

    def validate(self, attrs):
        """
        اعتبارسنجی سفارشی برای SyncLog.
        """
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')

        if start_time and end_time and start_time > end_time:
            raise serializers.ValidationError("Start time cannot be after end time.")

        if attrs.get('records_synced') < 0:
            raise serializers.ValidationError("Records synced cannot be negative.")

        return attrs

# --- سریالایزر MarketDataCache ---
class MarketDataCacheSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataCache
        fields = '__all__'

    def validate_latest_snapshot(self, value):
        """
        اعتبارسنجی ساختار داده latest_snapshot (اختیاری).
        مثلاً می‌توانید بررسی کنید که فیلدهای کلیدی وجود داشته باشند.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Latest snapshot must be a dictionary.")
        # مثال ساده: بررسی وجود یک کلید اساسی
        # required_keys = ['timestamp', 'close_price']
        # for key in required_keys:
        #     if key not in value:
        #         raise serializers.ValidationError(f"Key '{key}' is required in latest_snapshot.")
        return value
