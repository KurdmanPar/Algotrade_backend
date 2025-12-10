# apps/market_data/signals.py

from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)
from .tasks import process_tick_data_task # فرض بر این است که این تاسک وجود دارد
from apps.core.models import AuditLog # فرض بر این است که یک مدل کلی برای لاگ وجود دارد
from apps.agents.models import Agent # فرض بر این است که مدل Agent وجود دارد (برای ارتباط با عامل داده)

logger = logging.getLogger(__name__)

# --- سیگنال‌های DataSource ---
@receiver(post_save, sender=DataSource)
def handle_datasource_save(sender, instance, created, **kwargs):
    """
    Signal handler for DataSource model save events.
    Can be used for actions like:
    - Logging the creation/update.
    - Triggering a check for active configs related to this source.
    """
    action = 'CREATED' if created else 'UPDATED'
    logger.info(f"DataSource {instance.name} was {action.lower()}.")
    # مثال: ثبت واقعه در سیستم Audit Log
    AuditLog.objects.create(
        user=getattr(instance, 'modified_by', None), # اگر فیلد modified_by وجود داشت
        action=action,
        target_model='DataSource',
        target_id=instance.id,
        details=f"DataSource {instance.name} was {action.lower()}."
    )

    # مثال: چک کردن وضعیت کانفیگ‌های مرتبط بعد از به‌روزرسانی منبع
    if not created: # فقط برای بروزرسانی
        from .services import MarketDataService
        related_configs = MarketDataConfig.objects.filter(data_source=instance)
        for config in related_configs:
            MarketDataService.sync_config_status_with_source(config)


# --- سیگنال‌های MarketDataConfig ---
@receiver(post_save, sender=MarketDataConfig)
def handle_market_data_config_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataConfig model save events.
    Can be used for actions like:
    - Creating a default cache entry.
    - Triggering an initial sync if is_historical is True.
    - Updating related agents.
    """
    if created:
        # مثال: ایجاد یک ورودی کش پیش‌فرض
        MarketDataCache.objects.get_or_create(
            config=instance,
            defaults={'cached_at': timezone.now()}
        )
        logger.info(f"Default cache entry created for new MarketDataConfig {instance.id}.")

        # مثال: فعال‌سازی همگام‌سازی اولیه اگر نیاز باشد
        if instance.is_historical:
            from .services import MarketDataService
            try:
                # فقط اگر آخرین همگام‌سازی خیلی давقت نبوده باشد
                if not instance.last_sync_at or (timezone.now() - instance.last_sync_at) > timezone.timedelta(hours=1):
                    sync_log = MarketDataService.trigger_historical_sync(instance)
                    logger.info(f"Initial historical sync triggered for new config {instance.id} via signal.")
            except Exception as e:
                logger.error(f"Failed to trigger initial sync for new config {instance.id} in signal: {str(e)}")

    # مثال: اگر وضعیت کانفیگ تغییر کرد، عامل‌های مرتبط را اطلاع‌رسانی کنید
    # این نیازمند یک رابط ManyToMany یا یک مدل میانی بین Agent و MarketDataConfig است
    # if instance.status == 'SUBSCRIBED':
    #     linked_agents = instance.agents.all() # فرض بر این است که چنین رابطه‌ای وجود دارد
    #     for agent in linked_agents:
    #         agent.notify_config_change(instance) # یک متد سفارشی در مدل Agent


@receiver(post_delete, sender=MarketDataConfig)
def handle_market_data_config_delete(sender, instance, **kwargs):
    """
    Signal handler for MarketDataConfig model delete events.
    Can be used for actions like:
    - Deleting related cache entries.
    - Logging the deletion.
    - Revoking subscriptions on the data source (if applicable and safe).
    """
    logger.info(f"MarketDataConfig {instance.id} for {instance.instrument.symbol} on {instance.data_source.name} is being deleted.")
    # حذف ورودی کش مرتبط
    MarketDataCache.objects.filter(config=instance).delete()
    logger.info(f"Cache entry deleted for config {instance.id}.")

    # مثال: ثبت واقعه در سیستم Audit Log
    AuditLog.objects.create(
        user=getattr(instance, 'modified_by', None),
        action='DELETED',
        target_model='MarketDataConfig',
        target_id=instance.id,
        details=f"Config for {instance.instrument.symbol} ({instance.timeframe}) on {instance.data_source.name} was deleted."
    )

    # توجه: لغو اشتراک در صرافی باید با احتیاط و جداگانه انجام شود، نه در این سیگنال
    # مگر اینکه منطق سیستم به این شکل باشد که حذف کانفیگ معادل لغو اشتراک باشد


# --- سیگنال‌های MarketDataSnapshot ---
@receiver(post_save, sender=MarketDataSnapshot)
def handle_market_data_snapshot_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataSnapshot model save events.
    Can be used for actions like:
    - Updating the cache with the latest snapshot.
    - Triggering real-time analysis tasks.
    - Calculating rolling indicators (if done here, though a task is often better).
    """
    if created:
        logger.info(f"New MarketDataSnapshot saved for {instance.config.instrument.symbol} at {instance.timestamp}.")

        # مثال: بروزرسانی کش
        from .services import MarketDataService
        latest_data_dict = {
            'timestamp': instance.timestamp.timestamp(),
            'open': float(instance.open_price),
            'high': float(instance.high_price),
            'low': float(instance.low_price),
            'close': float(instance.close_price),
            'volume': float(instance.volume),
            # سایر فیلدها اگر نیاز باشد
        }
        MarketDataService.update_cache_for_config(instance.config, latest_data_dict, data_type='OHLCV')

        # مثال: فعال‌سازی تاسک تحلیل بلادرنگ (مثلاً بررسی الگوی قیمتی، ایجاد سیگنال)
        # from apps.analysis.tasks import analyze_snapshot_task
        # analyze_snapshot_task.delay(instance.id)


# --- سیگنال‌های MarketDataTick ---
@receiver(post_save, sender=MarketDataTick)
def handle_market_data_tick_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataTick model save events.
    Often triggers a background task for further processing due to high frequency.
    """
    if created:
        logger.debug(f"New MarketDataTick saved for {instance.config.instrument.symbol} at {instance.timestamp}.")
        # مثال: فعال‌سازی تاسک پردازش تیک در پس‌زمینه
        process_tick_data_task.delay(instance.id)

        # مثال: بروزرسانی کش (اگر معنادار باشد، مثلاً آخرین قیمت تیک)
        from .services import MarketDataService
        latest_tick_data = {
            'timestamp': instance.timestamp.timestamp(),
            'price': float(instance.price),
            'quantity': float(instance.quantity),
            'side': instance.side
        }
        MarketDataService.update_cache_for_config(instance.config, latest_tick_data, data_type='TICK')


# --- سیگنال‌های MarketDataOrderBook ---
@receiver(post_save, sender=MarketDataOrderBook)
def handle_market_data_orderbook_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataOrderBook model save events.
    Can be used for actions like:
    - Updating the cache with the latest order book snapshot.
    - Triggering tasks for order flow analysis.
    """
    if created:
        logger.info(f"New MarketDataOrderBook saved for {instance.config.instrument.symbol} at {instance.timestamp}.")

        # مثال: بروزرسانی کش
        from .services import MarketDataService
        latest_book_data = {
            'timestamp': instance.timestamp.timestamp(),
            'bids': instance.bids,
            'asks': instance.asks,
            'sequence': instance.sequence,
            'checksum': instance.checksum
        }
        MarketDataService.update_cache_for_config(instance.config, latest_book_data, data_type='ORDER_BOOK')

        # مثال: فعال‌سازی تاسک تحلیل کتاب سفارش
        # from apps.analysis.tasks import analyze_order_book_task
        # analyze_order_book_task.delay(instance.id)


# --- سیگنال‌های MarketDataSyncLog ---
@receiver(post_save, sender=MarketDataSyncLog)
def handle_market_data_sync_log_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataSyncLog model save events.
    Can be used for actions like:
    - Sending alerts if sync fails.
    - Updating metrics.
    - Logging the sync outcome.
    """
    if created:
        log_msg = f"Sync Log created for config {instance.config.id}. Status: {instance.status}, Records: {instance.records_synced}."
        if instance.status == 'FAILED':
            logger.error(log_msg)
            # مثال: ارسال ایمیل/پیامک هشدار
            # send_alert_to_admins(log_msg)
        elif instance.status == 'PARTIAL':
            logger.warning(log_msg)
        else: # SUCCESS
            logger.info(log_msg)

        # مثال: بروزرسانی معیارهای عملکرد (مثلاً در یک سرویس متریک یا مستقیماً در پایگاه داده)
        # from apps.monitoring.service import MetricsService
        # MetricsService.update_sync_metrics(instance)


# --- سیگنال‌های MarketDataCache ---
@receiver(pre_save, sender=MarketDataCache)
def handle_market_data_cache_pre_save(sender, instance, **kwargs):
    """
    Signal handler for MarketDataCache model pre-save events.
    Can be used for actions like:
    - Calculating checksums before saving.
    - Compressing data if needed.
    """
    # مثال: محاسبه چک‌سام داده (اگر نیاز باشد)
    # import hashlib
    # instance.checksum = hashlib.md5(str(instance.latest_snapshot).encode()).hexdigest()

@receiver(post_save, sender=MarketDataCache)
def handle_market_data_cache_save(sender, instance, created, **kwargs):
    """
    Signal handler for MarketDataCache model save events.
    Can be used for actions like:
    - Logging cache updates.
    - Evicting old entries if size exceeds a limit (logic should be implemented carefully).
    """
    action = 'CREATED' if created else 'UPDATED'
    logger.debug(f"MarketDataCache for config {instance.config.id} was {action.lower()}. Cached at: {instance.cached_at}")

# سایر سیگنال‌های مورد نیاز می‌توانند اضافه شوند
