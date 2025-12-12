# apps/instruments/signals.py

from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from .models import (
    Instrument,
    InstrumentExchangeMap,
    Indicator,
    IndicatorTemplate,
    PriceActionPattern,
    SmartMoneyConcept,
    AIMetric,
    InstrumentWatchlist,
)
from .tasks import (
    trigger_initial_data_sync_for_instrument_task, # مثال: فعال‌سازی همگام‌سازی اولیه داده
    notify_agents_of_instrument_change_task,       # مثال: اطلاع‌رسانی به عامل‌های داده
    update_indicator_cache_task,                  # مثال: بروزرسانی کش اندیکاتور
    process_new_watchlist_item_task,              # مثال: پردازش اضافه شدن نماد جدید به لیست نظارت
    cleanup_watchlist_item_task,                  # مثال: پاکسازی زمان حذف نماد از لیست
)
from .exceptions import InstrumentValidationError # فرض بر این است که این استثنا وجود دارد
from apps.core.logging import get_logger # فرض بر این است که یک سیستم لاگ مرکزی دارید

logger = get_logger(__name__) # استفاده از سیستم لاگ مرکزی

# --- سیگنال‌های Instrument ---
@receiver(post_save, sender=Instrument)
def handle_instrument_save(sender, instance, created, **kwargs):
    """
    Signal handler for Instrument model save events.
    Performs actions like:
    - Triggering an initial data sync if the instrument is newly created and active.
    - Notifying data collection agents about the new/updated instrument.
    - Logging the event.
    """
    if created:
        logger.info(f"New instrument '{instance.symbol}' was created.")
        # مثال: فعال‌سازی تاسک همگام‌سازی داده اولیه
        if instance.is_active:
            trigger_initial_data_sync_for_instrument_task.delay(instance.id)
        # مثال: اطلاع‌رسانی به عامل‌های مرتبط
        notify_agents_of_instrument_change_task.delay(instance.id, 'CREATED')

    else:
        logger.info(f"Instrument '{instance.symbol}' was updated.")
        # مثال: اگر وضعیت یا ویژگی‌های مهم تغییر کرد، عامل‌ها را مطلع کن
        # if 'is_active' in kwargs.get('update_fields', []) or 'tick_size' in kwargs.get('update_fields', []):
        notify_agents_of_instrument_change_task.delay(instance.id, 'UPDATED')

@receiver(pre_delete, sender=Instrument)
def handle_instrument_delete(sender, instance, **kwargs):
    """
    Signal handler for Instrument model delete events.
    Performs actions like:
    - Logging the deletion.
    - Notifying agents about the deletion (so they can stop monitoring).
    - Potentially triggering a cleanup task.
    """
    logger.info(f"Instrument '{instance.symbol}' is being deleted.")
    # مثال: اطلاع‌رسانی به عامل‌ها در مورد حذف
    notify_agents_of_instrument_change_task.delay(instance.id, 'DELETED')
    # مثال: تاسک پاکسازی مرتبط (مثلاً حذف داده‌های قدیمی)
    # cleanup_data_for_deleted_instrument_task.delay(instance.id)


# --- سیگنال‌های InstrumentExchangeMap ---
@receiver(post_save, sender=InstrumentExchangeMap)
def handle_instrument_exchange_map_save(sender, instance, created, **kwargs):
    """
    Signal handler for InstrumentExchangeMap save events.
    Can trigger actions like:
    - Starting a data feed subscription for the new mapping.
    - Updating exchange-specific configurations for the instrument.
    """
    if created:
        logger.info(f"New exchange mapping created for '{instance.instrument.symbol}' on '{instance.exchange.name}'.")
        # مثال: فعال‌سازی تاسک برای شروع اشتراک داده
        # start_data_subscription_task.delay(instance.id)
    else:
        logger.info(f"Exchange mapping for '{instance.instrument.symbol}' on '{instance.exchange.name}' was updated.")
        # مثال: اگر ویژگی‌های مهم تغییر کرد، ممکن است نیاز به بازسازی اشتراک یا بروزرسانی کش باشد
        # if any(field in kwargs.get('update_fields', []) for field in ['tick_size', 'lot_size', 'min_notional']):
        #    update_cache_or_subscription_task.delay(instance.id)

@receiver(pre_delete, sender=InstrumentExchangeMap)
def handle_instrument_exchange_map_delete(sender, instance, **kwargs):
    """
    Signal handler for InstrumentExchangeMap delete events.
    Logs the event and potentially triggers cleanup.
    """
    logger.info(f"Exchange mapping for '{instance.instrument.symbol}' on '{instance.exchange.name}' is being deleted.")
    # مثال: تاسک پاکسازی یا لغو اشتراک
    # unsubscribe_from_data_feed_task.delay(instance.id)


# --- سیگنال‌های Indicator ---
@receiver(post_save, sender=Indicator)
def handle_indicator_save(sender, instance, created, **kwargs):
    """
    Signal handler for Indicator model save events.
    Can trigger actions like:
    - Updating related caches.
    - Notifying analysis agents.
    """
    if created:
        logger.info(f"New indicator '{instance.name}' ({instance.code}) was created.")
    else:
        logger.info(f"Indicator '{instance.name}' ({instance.code}) was updated.")
        # اگر منطق محاسباتی تغییر کرده باشد، ممکن است نیاز به بازسازی کش یا اطلاع‌رسانی به عامل‌های تحلیلی باشد
        if 'calculation_logic' in kwargs.get('update_fields', []): # اگر چنین فیلدی وجود داشت
            update_indicator_cache_task.delay(instance.id)
            # notify_analysis_agents_task.delay(instance.id, 'LOGIC_CHANGED')

@receiver(pre_delete, sender=Indicator)
def handle_indicator_delete(sender, instance, **kwargs):
    """
    Signal handler for Indicator model delete events.
    Logs the event.
    """
    logger.info(f"Indicator '{instance.name}' ({instance.code}) is being deleted.")


# --- سیگنال‌های IndicatorTemplate ---
@receiver(post_save, sender=IndicatorTemplate)
def handle_indicator_template_save(sender, instance, created, **kwargs):
    """
    Signal handler for IndicatorTemplate save events.
    Can trigger actions like:
    - Applying the template's config to instruments if auto_apply is True.
    """
    if not created and instance.auto_apply: # فقط برای بروزرسانی و اگر auto_apply فعال شده باشد
        # مثال: فعال‌سازی تاسک برای اعمال الگو به نمادهای مشخص
        # apply_template_to_instruments_task.delay(instance.id)
        pass # منطق مربوطه اینجا قرار می‌گیرد

@receiver(pre_delete, sender=IndicatorTemplate)
def handle_indicator_template_delete(sender, instance, **kwargs):
    """
    Signal handler for IndicatorTemplate delete events.
    Logs the event.
    """
    logger.info(f"Indicator template '{instance.name}' is being deleted.")


# --- سیگنال‌های InstrumentWatchlist (M2M) ---
@receiver(m2m_changed, sender=InstrumentWatchlist.instruments.through)
def handle_watchlist_instruments_change(sender, instance, action, pk_set, reverse, model, **kwargs):
    """
    Signal handler for changes to the instruments in an InstrumentWatchlist (M2M relation).
    Performs actions based on the type of change (add, remove, clear).
    """
    if action == 'post_add':
        logger.info(f"Items added to watchlist '{instance.name}' by {instance.owner.username}.")
        for instrument_pk in pk_set:
            # مثال: فعال‌سازی تاسک پردازش برای هر نماد اضافه شده
            process_new_watchlist_item_task.delay(instance.id, instrument_pk)
    elif action == 'post_remove':
        logger.info(f"Items removed from watchlist '{instance.name}' by {instance.owner.username}.")
        for instrument_pk in pk_set:
            # مثال: فعال‌سازی تاسک پاکسازی برای هر نماد حذف شده
            cleanup_watchlist_item_task.delay(instance.id, instrument_pk)
    elif action == 'post_clear':
        logger.info(f"All items cleared from watchlist '{instance.name}' by {instance.owner.username}.")
        # مثال: فعال‌سازی تاسک پاکسازی کامل
        # cleanup_all_watchlist_items_task.delay(instance.id)


# --- سایر سیگنال‌های مرتبط ---
# می‌توانید برای سایر مدل‌هایی که در instruments تعریف کرده‌اید نیز سیگنال بنویسید
# مثلاً برای PriceActionPattern، SmartMoneyConcept، AIMetric و غیره.

# مثال: زمانی که یک نماد به لیست نظارتی اضافه یا حذف می‌شود، یک کار را اجرا کن
# @receiver(m2m_changed, sender=InstrumentWatchlist.instruments.through)
# def on_watchlist_instruments_changed(sender, instance, action, reverse, model, pk_set, **kwargs):
#     if action == 'post_add':
#         for instrument_pk in pk_set:
#             # مثلاً فعال‌سازی یک عامل نظارت برای نماد جدید
#             # start_monitoring_agent_for_instrument.delay(instance.id, instrument_pk)
#             pass
#     elif action == 'post_remove':
#         for instrument_pk in pk_set:
#             # مثلاً توقف یک عامل نظارت
#             # stop_monitoring_agent_for_instrument.delay(instance.id, instrument_pk)
#             pass

# --- مثال پیشرفته: اعتبارسنجی در سیگنال (نامناسب‌تر از validate در مدل یا سریالایزر، اما گاهی مفید) ---
# @receiver(pre_save, sender=Instrument)
# def validate_instrument_before_save(sender, instance, **kwargs):
#     """
#     Validates an instrument before saving based on complex logic involving other models or services.
#     This is generally less preferred than model.clean() or serializer validation.
#     """
#     # مثال: چک کردن اینکه آیا نماد در یک گروه خاص از نمادهای دیگر متفاوت است
#     # if instance.group.name == 'Crypto' and instance.category.name == 'Stock':
#     #     raise InstrumentValidationError("Crypto instruments cannot have 'Stock' category.")
#     pass # منطق مورد نیاز اینجا قرار می‌گیرد

logger.info("Signals for 'instruments' app loaded successfully.")
