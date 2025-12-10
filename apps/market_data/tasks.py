# apps/market_data/tasks.py

from celery import shared_task
import logging
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
)
from .services import MarketDataService
from .exceptions import DataSyncError, DataFetchError # فرض بر این است که این استثناها وجود دارند
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویس وجود دارد
from apps.core.encryption import decrypt_field # فرض بر این است که این تابع وجود دارد

logger = logging.getLogger(__name__)

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def fetch_and_store_historical_data_task(self, config_id: int, sync_log_id: int):
    """
    Celery task for fetching historical market data based on a MarketDataConfig
    and storing it in the database. Updates the MarketDataSyncLog upon completion.
    Uses exponential backoff for retries.
    """
    try:
        # 1. دریافت کانفیگ و SyncLog
        try:
            config = MarketDataConfig.objects.select_related('data_source', 'instrument').get(id=config_id)
            sync_log = MarketDataSyncLog.objects.get(id=sync_log_id)
        except ObjectDoesNotExist as e:
            logger.error(f"Config (ID: {config_id}) or SyncLog (ID: {sync_log_id}) not found in task: {e}")
            # ممکن است بخواهید SyncLog را نیز به روز کنید
            if 'sync_log' in locals():
                 sync_log.status = 'FAILED'
                 sync_log.error_message = str(e)
                 sync_log.end_time = timezone.now()
                 sync_log.save(update_fields=['status', 'error_message', 'end_time'])
            return

        logger.info(f"Starting historical sync task for config {config.id} (Symbol: {config.instrument.symbol}, TF: {config.timeframe}).")

        # 2. شروع زمان‌بندی
        start_time = timezone.now()

        # 3. دریافت کانکتور
        connector = ConnectorService(config.data_source.name)

        # 4. بازه زمانی را مشخص کنید (مثلاً آخرین داده ذخیره شده تا الان)
        # فرض بر این است که last_sync_at در کانفیگ ذخیره می‌شود
        since_timestamp = None
        if config.last_sync_at:
            since_timestamp = int(config.last_sync_at.timestamp() * 1000) # تبدیل به میلی‌ثانیه (بسته به API)
        else:
            # اگر هیچ همگام‌سازی قبلی نداشته باشیم، ممکن است بخواهیم یک بازه پیش‌فرض تعیین کنیم
            # مثلاً 1 روز قبل
            since_timestamp = int((timezone.now() - timezone.timedelta(days=1)).timestamp() * 1000)

        # 5. دریافت داده از کانکتور
        try:
            raw_data = connector.fetch_historical_data(
                symbol=config.instrument.symbol,
                timeframe=config.timeframe,
                since=since_timestamp,
                limit=1000, # ممکن است لازم باشد داده را چندین بار درخواست کنید
                params={} # پارامترهای اختیاری مانند نوع داده (OHLCV, TICK)
            )
        except Exception as e:
            logger.error(f"Error fetching historical data for config {config.id} in task: {str(e)}")
            sync_log.status = 'FAILED'
            sync_log.error_message = str(e)
            sync_log.end_time = timezone.now()
            sync_log.save(update_fields=['status', 'error_message', 'end_time'])
            return

        # 6. پردازش و ذخیره داده
        records_synced_count = 0
        for raw_candle_or_tick in raw_data:
            # چون داده ممکن است TICK یا OHLCV باشد، باید نوع کانفیگ را چک کنیم
            if config.data_type == 'OHLCV':
                # استفاده از سرویس برای پردازش
                try:
                    MarketDataService.process_received_snapshot_data(config, raw_candle_or_tick)
                    records_synced_count += 1
                except Exception as e:
                    logger.warning(f"Failed to process snapshot data {raw_candle_or_tick} for config {config.id} in task: {str(e)}")
                    # ممکن است بخواهید ادامه دهید و فقط خطاها را لاگ کنید
                    continue
            elif config.data_type == 'TICK':
                 try:
                     MarketDataService.process_received_tick_data(config, raw_candle_or_tick)
                     records_synced_count += 1
                 except Exception as e:
                     logger.warning(f"Failed to process tick data {raw_candle_or_tick} for config {config.id} in task: {str(e)}")
                     continue
            # سایر انواع داده...

        # 7. پایان زمان‌بندی و به‌روزرسانی SyncLog
        end_time = timezone.now()
        duration = end_time - start_time

        sync_log.start_time = start_time
        sync_log.end_time = end_time
        sync_log.records_synced = records_synced_count
        sync_log.status = 'SUCCESS' if records_synced_count > 0 else 'PARTIAL' # یا FAILED اگر هیچ چیزی نباشد؟
        sync_log.details = {'duration_seconds': duration.total_seconds(), 'task_id': self.request.id}
        sync_log.save(update_fields=['start_time', 'end_time', 'records_synced', 'status', 'details'])

        # 8. بروزرسانی last_sync_at در کانفیگ
        config.last_sync_at = end_time
        config.save(update_fields=['last_sync_at'])

        logger.info(f"Historical sync task completed for config {config.id}. Synced {records_synced_count} records in {duration.total_seconds()} seconds.")

    except DataFetchError as e:
        logger.error(f"DataFetchError in historical sync task for config {config_id}: {str(e)}")
        # ممکن است بخواهید SyncLog را نیز به روز کنید
        if 'sync_log' in locals():
             sync_log.status = 'FAILED'
             sync_log.error_message = str(e)
             sync_log.end_time = timezone.now()
             sync_log.save(update_fields=['status', 'error_message', 'end_time'])
        raise # Celery retry
    except DataSyncError as e:
        logger.error(f"DataSyncError in historical sync task for config {config_id}: {str(e)}")
        if 'sync_log' in locals():
             sync_log.status = 'FAILED'
             sync_log.error_message = str(e)
             sync_log.end_time = timezone.now()
             sync_log.save(update_fields=['status', 'error_message', 'end_time'])
        raise # Celery retry
    except Exception as e:
        logger.error(f"Unexpected error in historical sync task for config {config_id}: {str(e)}")
        if 'sync_log' in locals():
             sync_log.status = 'FAILED'
             sync_log.error_message = str(e)
             sync_log.end_time = timezone.now()
             sync_log.save(update_fields=['status', 'error_message', 'end_time'])
        raise # Celery retry


@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 30})
def process_tick_data_task(self, tick_id: int):
    """
    Celery task for processing a single tick of data after it's saved.
    This could involve calculating indicators, triggering alerts, or feeding into ML models.
    """
    try:
        tick = MarketDataTick.objects.select_related('config__instrument', 'config__data_source').get(id=tick_id)
        logger.info(f"Processing tick data task for ID {tick_id} (Symbol: {tick.config.instrument.symbol}).")

        # منطق پردازش تیک: مثلاً محاسبه VWAP، بررسی شرایط خرید/فروش، ارسال به سایر عامل‌ها
        # این بخش می‌تواند پیچیده باشد و به سایر سرویس‌ها وابسته باشد
        # مثال ساده:
        current_price = tick.price
        volume = tick.volume
        # ... محاسبات ...

        # مثال: ارسال به یک عامل تحلیلی
        # from apps.analysis.tasks import analyze_tick_task
        # analyze_tick_task.delay(tick.id)

        logger.info(f"Tick data processing task completed for ID {tick_id}.")

    except MarketDataTick.DoesNotExist:
        logger.error(f"MarketDataTick with id {tick_id} not found in process_tick_data_task.")
    except Exception as e:
        logger.error(f"Error in process_tick_data_task for tick ID {tick_id}: {str(e)}")
        raise # Celery retry


@shared_task(bind=True)
def cleanup_old_snapshots_task(self, days_to_keep: int = 30):
    """
    Celery task for periodically cleaning up old MarketDataSnapshot records.
    This should be scheduled using Celery Beat.
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
        deleted_count, _ = MarketDataSnapshot.objects.filter(timestamp__lt=cutoff_date).delete()
        logger.info(f"Cleanup task removed {deleted_count} snapshots older than {days_to_keep} days.")
    except Exception as e:
        logger.error(f"Error in cleanup_old_snapshots_task: {str(e)}")
        raise # Celery retry


@shared_task(bind=True)
def cleanup_old_orderbooks_task(self, days_to_keep: int = 7):
    """
    Celery task for periodically cleaning up old MarketDataOrderBook records.
    This should be scheduled using Celery Beat.
    """
    try:
        cutoff_date = timezone.now() - timezone.timedelta(days=days_to_keep)
        deleted_count, _ = MarketDataOrderBook.objects.filter(timestamp__lt=cutoff_date).delete()
        logger.info(f"Cleanup task removed {deleted_count} order books older than {days_to_keep} days.")
    except Exception as e:
        logger.error(f"Error in cleanup_old_orderbooks_task: {str(e)}")
        raise # Celery retry

# سایر تاسک‌های مرتبط می‌توانند اضافه شوند
# مثلاً:
# - تاسک برای همگام‌سازی داده‌های نمادها از صرافی‌ها
# - تاسک برای محاسبه نمادهای جدید یا شاخص‌ها
# - تاسک برای ارسال گزارش‌های دوره‌ای
# - تاسک برای مدیریت کش
