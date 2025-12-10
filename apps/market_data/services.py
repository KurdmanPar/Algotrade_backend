# apps/market_data/services.py

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)
from .exceptions import DataSyncError, DataFetchError, DataProcessingError # فرض بر این است که این استثناها وجود دارند
from .helpers import normalize_data_from_source, validate_ohlcv_data # فرض بر این است که این توابع کمکی وجود دارند
from .tasks import fetch_and_store_historical_data_task, process_tick_data_task # فرض بر این است که این تاسک‌ها وجود دارند
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویس برای اتصال به APIها وجود دارد
from apps.core.encryption import decrypt_field # فرض بر این است که این تابع برای رمزنگاری کلیدها وجود دارد

logger = logging.getLogger(__name__)

class MarketDataService:
    """
    Service class for handling market data-related business logic.
    This includes data synchronization, subscription management, data processing,
    and interaction with external APIs and other services.
    """

    @staticmethod
    def trigger_historical_sync(config: MarketDataConfig) -> MarketDataSyncLog:
        """
        Initiates a historical data sync for a given config.
        Creates a SyncLog entry and delegates the heavy lifting to a Celery task.
        """
        try:
            start_time = timezone.now()
            # ایجاد یک رکورد SyncLog اولیه
            sync_log = MarketDataSyncLog.objects.create(
                config=config,
                start_time=start_time,
                status='PENDING', # وضعیت شروع
                details={'triggered_by': 'api_call', 'historical_sync': True}
            )

            # فعال‌سازی تاسک Celery برای دریافت و ذخیره داده‌های تاریخی
            # توجه: تاسک باید ID کانفیگ را دریافت کند، نه خود شیء
            fetch_and_store_historical_data_task.delay(config.id, sync_log.id)

            logger.info(f"Historical sync task triggered for config {config.id} via service.")
            return sync_log
        except Exception as e:
            logger.error(f"Error triggering historical sync for config {config.id} in service: {str(e)}")
            raise DataSyncError(f"Failed to trigger sync for config {config.id}: {str(e)}")


    @staticmethod
    def process_received_tick_data(config: MarketDataConfig, raw_tick_data: dict):
        """
        Processes a single tick of data received from an agent or WebSocket.
        Validates, normalizes, saves, and potentially triggers downstream actions.
        """
        try:
            # 1. نرمالایز کردن داده
            normalized_tick = normalize_data_from_source(raw_tick_data, config.data_source.name, 'TICK')
            if not normalized_tick:
                logger.warning(f"Failed to normalize tick data for config {config.id}. Raw data: {raw_tick_data}")
                return

            # 2. اعتبارسنجی داده
            validated_tick = validate_ohlcv_data(normalized_tick, 'TICK') # تابع کمکی فرضی
            if not validated_tick:
                logger.warning(f"Normalized tick data failed validation for config {config.id}. Normalized data: {normalized_tick}")
                return

            # 3. ذخیره در مدل MarketDataTick
            with transaction.atomic(): # برای اطمینان از یکپارچگی
                tick_obj = MarketDataTick.objects.create(
                    config=config,
                    timestamp=timezone.make_aware(datetime.fromtimestamp(validated_tick['timestamp'])),
                    price=Decimal(str(validated_tick['price'])),
                    quantity=Decimal(str(validated_tick['quantity'])),
                    side=validated_tick['side'],
                    trade_id=validated_tick.get('trade_id', None)
                )

            logger.info(f"Processed and saved tick data for {config.instrument.symbol} (ID: {config.id}). Timestamp: {tick_obj.timestamp}")

            # 4. ارسال به تاسک پردازش (مثلاً محاسبه VWAP، ارسال به سایر عامل‌ها)
            process_tick_data_task.delay(tick_obj.id)

        except ValidationError as ve:
            logger.error(f"Validation error processing tick for config {config.id}: {ve}")
            raise DataProcessingError(f"Validation failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Error processing tick data for config {config.id} in service: {str(e)}")
            raise DataProcessingError(f"Failed to process tick: {str(e)}")


    @staticmethod
    def process_received_snapshot_data(config: MarketDataConfig, raw_snapshot_data: dict):
        """
        Processes a single snapshot of OHLCV data received from an agent or API.
        Validates, normalizes, saves, and potentially updates cache.
        """
        try:
            # 1. نرمالایز کردن داده
            normalized_snapshot = normalize_data_from_source(raw_snapshot_data, config.data_source.name, 'OHLCV')
            if not normalized_snapshot:
                logger.warning(f"Failed to normalize snapshot data for config {config.id}. Raw data: {raw_snapshot_data}")
                return

            # 2. اعتبارسنجی داده OHLCV
            validated_snapshot = validate_ohlcv_data(normalized_snapshot, 'OHLCV')
            if not validated_snapshot:
                logger.warning(f"Normalized snapshot data failed validation for config {config.id}. Normalized data: {normalized_snapshot}")
                return

            # 3. ذخیره در مدل MarketDataSnapshot
            with transaction.atomic():
                snapshot_obj = MarketDataSnapshot.objects.create(
                    config=config,
                    timestamp=timezone.make_aware(datetime.fromtimestamp(validated_snapshot['timestamp'])),
                    open_price=Decimal(str(validated_snapshot['open'])),
                    high_price=Decimal(str(validated_snapshot['high'])),
                    low_price=Decimal(str(validated_snapshot['low'])),
                    close_price=Decimal(str(validated_snapshot['close'])),
                    volume=Decimal(str(validated_snapshot['volume'])),
                    best_bid=Decimal(str(validated_snapshot.get('best_bid', 0))) if validated_snapshot.get('best_bid') else None,
                    best_ask=Decimal(str(validated_snapshot.get('best_ask', 0))) if validated_snapshot.get('best_ask') else None,
                    bid_size=Decimal(str(validated_snapshot.get('bid_size', 0))) if validated_snapshot.get('bid_size') else None,
                    ask_size=Decimal(str(validated_snapshot.get('ask_size', 0))) if validated_snapshot.get('ask_size') else None,
                    additional_data=validated_snapshot.get('additional_data', {})
                )

            logger.info(f"Processed and saved snapshot data for {config.instrument.symbol} (ID: {config.id}). Timestamp: {snapshot_obj.timestamp}")

            # 4. بروزرسانی کش (اختیاری)
            MarketDataService.update_cache_for_config(config, validated_snapshot)

        except ValidationError as ve:
            logger.error(f"Validation error processing snapshot for config {config.id}: {ve}")
            raise DataProcessingError(f"Validation failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Error processing snapshot data for config {config.id} in service: {str(e)}")
            raise DataProcessingError(f"Failed to process snapshot: {str(e)}")


    @staticmethod
    def process_received_orderbook_data(config: MarketDataConfig, raw_orderbook_data: dict):
        """
        Processes an order book snapshot received from an agent or WebSocket.
        Validates, normalizes, saves.
        """
        try:
            # 1. نرمالایز کردن داده
            normalized_book = normalize_data_from_source(raw_orderbook_data, config.data_source.name, 'ORDER_BOOK')
            if not normalized_book:
                logger.warning(f"Failed to normalize order book data for config {config.id}. Raw data: {raw_orderbook_data}")
                return

            # 2. اعتبارسنجی داده OrderBook (مثلاً ساختار bids/asks)
            # این بخش را می‌توان در تابع کمکی جداگانه نوشت
            bids = normalized_book.get('bids', [])
            asks = normalized_book.get('asks', [])
            sequence = normalized_book.get('sequence')
            checksum = normalized_book.get('checksum')

            # ساده‌ترین اعتبارسنجی: بررسی اینکه bids و asks لیست هستند
            if not isinstance(bids, list) or not isinstance(asks, list):
                 logger.warning(f"Invalid order book format (bids/asks not lists) for config {config.id}. Normalized data: {normalized_book}")
                 return

            # 3. ذخیره در مدل MarketDataOrderBook
            with transaction.atomic():
                book_obj = MarketDataOrderBook.objects.create(
                    config=config,
                    timestamp=timezone.make_aware(datetime.fromtimestamp(normalized_book['timestamp'])),
                    bids=bids,
                    asks=asks,
                    sequence=sequence,
                    checksum=checksum
                )

            logger.info(f"Processed and saved order book data for {config.instrument.symbol} (ID: {config.id}). Timestamp: {book_obj.timestamp}")

            # 4. بروزرسانی کش (اختیاری)
            MarketDataService.update_cache_for_config(config, normalized_book, data_type='ORDER_BOOK')

        except ValidationError as ve:
            logger.error(f"Validation error processing order book for config {config.id}: {ve}")
            raise DataProcessingError(f"Validation failed: {str(ve)}")
        except Exception as e:
            logger.error(f"Error processing order book data for config {config.id} in service: {str(e)}")
            raise DataProcessingError(f"Failed to process order book: {str(e)}")


    @staticmethod
    def update_cache_for_config(config: MarketDataConfig, data: dict, data_type: str = 'OHLCV'):
        """
        Updates the cache entry for a specific config with the latest data point.
        """
        try:
            cache_entry, created = MarketDataCache.objects.get_or_create(
                config=config,
                defaults={'latest_snapshot': data, 'cached_at': timezone.now()}
            )
            if not created:
                cache_entry.latest_snapshot = data
                cache_entry.cached_at = timezone.now()
                cache_entry.save(update_fields=['latest_snapshot', 'cached_at'])

            logger.debug(f"Cache updated for config {config.id} with data type {data_type}.")
        except Exception as e:
            logger.error(f"Error updating cache for config {config.id}: {str(e)}")
            # این خطا ممکن است نادیده گرفته شود یا به روشی دیگر مدیریت شود، چون کش اختیاری است


    @staticmethod
    def get_latest_snapshot_for_instrument(symbol: str, timeframe: str):
        """
        Retrieves the latest snapshot for a given instrument symbol and timeframe.
        Uses cache if available, otherwise queries the database.
        """
        try:
            # 1. تلاش برای گرفتن از کش
            try:
                config = MarketDataConfig.objects.get(
                    instrument__symbol__iexact=symbol,
                    timeframe__iexact=timeframe
                )
                cache_entry = MarketDataCache.objects.get(config=config)
                logger.debug(f"Cache hit for {symbol} ({timeframe}).")
                return cache_entry.latest_snapshot
            except (MarketDataConfig.DoesNotExist, MarketDataCache.DoesNotExist):
                logger.debug(f"Cache miss for {symbol} ({timeframe}), querying DB.")
                pass # ادامه دهید به کوئری پایگاه داده

            # 2. کوئری پایگاه داده
            latest_snapshot = MarketDataSnapshot.objects.filter(
                config__instrument__symbol__iexact=symbol,
                config__timeframe__iexact=timeframe
            ).latest('timestamp')

            serializer = MarketDataSnapshotSerializer(latest_snapshot)
            return serializer.data
        except MarketDataSnapshot.DoesNotExist:
            logger.info(f"No snapshot found in DB for {symbol} ({timeframe}).")
            return None
        except Exception as e:
            logger.error(f"Error fetching latest snapshot for {symbol} ({timeframe}) in service: {str(e)}")
            return None


    @staticmethod
    def sync_config_status_with_source(config: MarketDataConfig):
        """
        Checks the actual status of the subscription on the data source
        and updates the local config.status accordingly.
        This might involve calling the source's API to check active subscriptions.
        """
        try:
            connector = ConnectorService(config.data_source.name)
            # فرض بر این است که کانکتور متدی دارد که وضعیت اشتراک را بر اساس نماد، تایم‌فریم و غیره چک کند
            is_subscribed_on_source = connector.check_subscription_status(
                config.instrument.symbol,
                config.timeframe,
                config.data_type,
                credential=config.api_credential # فرض بر این است که api_credential در مدل وجود دارد یا قابل دسترسی است
            )

            new_status = 'SUBSCRIBED' if is_subscribed_on_source else 'UNSUBSCRIBED'
            if config.status != new_status:
                config.status = new_status
                config.save(update_fields=['status'])
                logger.info(f"Config {config.id} status updated to {new_status} based on source check.")

        except Exception as e:
            logger.error(f"Error syncing config {config.id} status with source: {str(e)}")
            # ممکن است بخواهید وضعیت را روی ERROR قرار دهید
            config.status = 'ERROR'
            config.save(update_fields=['status'])

    # سایر متدهای سرویس می‌توانند اضافه شوند
    # مثلاً:
    # - یک متد برای ایجاد یک کانفیگ جدید و اجرای یک همگام‌سازی اولیه
    # - یک متد برای دریافت یک بازه زمانی از داده‌ها از پایگاه داده
    # - یک متد برای مدیریت مجوزهای دسترسی به داده‌های خاص
    # - یک متد برای آمارگیری از داده‌های دریافتی
