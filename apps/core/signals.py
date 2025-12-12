# apps/core/signals.py

from django.db.models.signals import post_save, pre_delete, m2m_changed
from django.dispatch import receiver
from django.utils import timezone
from django.conf import settings
import logging
from .models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌هایی که در core تعریف شده‌اند
)
from .tasks import (
    log_audit_event_task, # فرض: این تاسک در apps/core/tasks.py تعریف شده است
    # ... سایر تاسک‌های مرتبط با core ...
)
from .services import AuditService, CacheService # فرض: این سرویس‌ها در apps/core/services.py تعریف شده است
from .helpers import get_client_ip # فرض: این تابع در apps/core/helpers.py تعریف شده است
from apps.accounts.models import CustomUser # فرض: مدل کاربر در این اپلیکیشن قرار دارد
from apps.instruments.models import Instrument # فرض: مدل نماد در این اپلیکشن قرار دارد
from apps.exchanges.models import ExchangeAccount # فرض: مدل حساب صرافی در این اپلیکشن قرار دارد

logger = logging.getLogger(__name__)

# --- سیگنال‌های مدل‌های Core ---

@receiver(post_save, sender=AuditLog)
def handle_audit_log_save(sender, instance, created, **kwargs):
    """
    Signal handler for AuditLog model save events.
    Can be used for actions like:
    - Sending audit logs to external systems (e.g., ELK stack, Syslog).
    - Triggering alerts if specific audit events occur.
    """
    if created:
        logger.info(f"Audit log entry created for action '{instance.action}' on {instance.target_model} ID {instance.target_id}.")

        # مثال: فعال‌سازی تاسک برای ارسال به سیستم لاگ خارجی
        # from apps.core.tasks import send_audit_log_to_external_system_task
        # send_audit_log_to_external_system_task.delay(instance.id)

        # مثال: چک کردن رویدادهای حساس
        sensitive_actions = ['CREATE_API_KEY', 'UPDATE_PASSWORD', 'DELETE_ACCOUNT', 'PLACE_LARGE_ORDER']
        if instance.action in sensitive_actions:
             # ارسال اعلان یا ایمیل هشدار
             logger.warning(f"Sensitive action '{instance.action}' detected for user {instance.user.email}.")

@receiver(post_save, sender=SystemSetting)
def handle_system_setting_save(sender, instance, created, **kwargs):
    """
    Signal handler for SystemSetting model save events.
    Can be used for actions like:
    - Clearing related caches when a setting changes.
    - Triggering a restart of dependent services if a critical setting is updated.
    - Logging the setting change.
    """
    if not created:
        # فقط هنگام بروزرسانی
        logger.info(f"System setting '{instance.key}' was updated.")
        # مثال: پاک کردن کش مرتبط با این تنظیم
        # cache_key = f"sys_setting_{instance.key.lower()}"
        # cache.delete(cache_key)
        # یا استفاده از سرویس کش
        CacheService.invalidate_cached_value(f"sys_setting_{instance.key.lower()}", delete_db_entry=False) # فقط کش خارجی را حذف کن

        # مثال: چک کردن تغییر در تنظیمات مهم
        critical_settings = ['GLOBAL_RATE_LIMIT_PER_MINUTE', 'DEFAULT_MARKET_DATA_BACKEND', 'ENABLE_REALTIME_SYNC']
        if instance.key in critical_settings:
             logger.warning(f"CRITICAL setting '{instance.key}' was changed. Review required.")
             # ممکن است نیاز به ارسال اعلان به ادمین باشد
             # send_alert_to_admins_task.delay(f"Setting {instance.key} was changed.")

    else:
        logger.info(f"New system setting '{instance.key}' was created.")


@receiver(post_save, sender=CacheEntry)
def handle_cache_entry_save(sender, instance, created, **kwargs):
    """
    Signal handler for CacheEntry model save events.
    Logs cache writes or updates.
    """
    if created:
        logger.info(f"New cache entry '{instance.key}' was created in DB cache.")
    else:
        logger.info(f"Cache entry '{instance.key}' was updated in DB cache.")


@receiver(pre_delete, sender=CacheEntry)
def handle_cache_entry_delete(sender, instance, **kwargs):
    """
    Signal handler for CacheEntry model delete events.
    Logs cache invalidations.
    """
    logger.info(f"Cache entry '{instance.key}' was invalidated/deleted from DB cache.")


# --- سیگنال‌های مدل‌های دامنه‌ای (اگر مربوط به core باشند) ---
# مثال: اگر مدل Instrument در core بود یا ارث برده بود از یک مدل core
# @receiver(post_save, sender=Instrument)
# def handle_instrument_save(sender, instance, created, **kwargs):
#     """
#     Signal handler for Instrument model save events.
#     Can trigger actions like:
#     - Notifying data collection agents about a new/updated instrument.
#     - Syncing instrument details with exchanges if needed.
#     """
#     if created:
#         logger.info(f"New instrument '{instance.symbol}' was created.")
#         # مثال: ارسال پیام به یک عامل جمع‌آوری داده
#         # from apps.agents.tasks import notify_data_collector_of_new_instrument_task
#         # notify_data_collector_of_new_instrument_task.delay(instance.id)
#     else:
#         logger.info(f"Instrument '{instance.symbol}' was updated.")
#         # مثال: اگر ویژگی‌های مهم تغییر کرد، عامل‌های مرتبط را مطلع کن
#         # if any(field in kwargs.get('update_fields', []) for field in ['tick_size', 'lot_size', 'is_active']):
#         #     from apps.agents.tasks import notify_agents_of_instrument_change_task
#         #     notify_agents_of_instrument_change_task.delay(instance.id, 'INSTRUMENT_UPDATED')


# --- سیگنال‌های مدل کاربر ---
# مثال: ایجاد یک پروفایل کاربر هنگام ایجاد کاربر (اگر از BaseOwnedModel استفاده نشود و پروفایل جداگانه باشد)
# این سیگنال معمولاً در اپلیکیشن accounts قرار می‌گیرد، اما اگر در core تعریف شود:
# @receiver(post_save, sender=CustomUser)
# def create_or_update_user_profile(sender, instance, created, **kwargs):
#     """
#     Creates or updates a user profile when a CustomUser is saved.
#     Assumes a UserProfile model exists and is linked via OneToOneField.
#     """
#     if created:
#         from apps.accounts.models import UserProfile # import داخل تابع برای جلوگیری از حلقه
#         UserProfile.objects.create(user=instance)
#         logger.info(f"Profile created automatically for new user: {instance.email}")
#     else:
#         # اگر پروفایل وجود نداشت، ایجاد کن (برای کاربران قبلی)
#         try:
#             instance.profile.save() # این باعث ایجاد می‌شود اگر وجود نداشته باشد
#         except UserProfile.DoesNotExist:
#             UserProfile.objects.create(user=instance)
#         logger.info(f"Profile for user {instance.email} saved/updated.")


# --- سیگنال‌های مرتبط با M2M ---
# مثال: زمانی که نماد جدیدی به یک لیست نظارتی اضافه یا حذف می‌شود
# این سیگنال معمولاً در اپلیکیشن instruments یا اپلیکیشنی که InstrumentWatchlist در آن تعریف شده است قرار می‌گیرد
# اما اگر مدل Watchlist در core تعریف شود:
# @receiver(m2m_changed, sender=InstrumentWatchlist.instruments.through)
# def handle_watchlist_instruments_change(sender, instance, action, reverse, model, pk_set, **kwargs):
#     if action == 'post_add':
#         for instrument_pk in pk_set:
#             logger.info(f"Instrument {instrument_pk} added to watchlist {instance.name}.")
#             # ممکن است نیاز به فعال‌سازی یک عامل نظارت یا تاسک تحلیلی داشته باشید
#             # from apps.analysis.tasks import start_monitoring_instrument_task
#             # start_monitoring_instrument_task.delay(instance.id, instrument_pk)
#     elif action == 'post_remove':
#         for instrument_pk in pk_set:
#             logger.info(f"Instrument {instrument_pk} removed from watchlist {instance.name}.")
#             # توقف یا بروزرسانی عامل مربوطه
#             # from apps.analysis.tasks import stop_monitoring_instrument_task
#             # stop_monitoring_instrument_task.delay(instance.id, instrument_pk)
#     elif action == 'post_clear':
#         logger.info(f"All instruments cleared from watchlist {instance.name}.")

# --- سایر سیگنال‌های ممکن ---
# می‌توانید سیگنال‌هایی برای مدل‌های دیگری که در apps/core/models.py تعریف می‌کنید نیز بنویسید
# مثلاً یک مدل LogEvent، SystemConfig، یا یک مدل مرتبط با MAS
# @receiver(post_save, sender=MASAgent)
# def handle_agent_status_change(sender, instance, created, **kwargs):
#     # ...

logger.info("Core signals loaded successfully.")
