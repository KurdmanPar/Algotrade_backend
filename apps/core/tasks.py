# apps/core/tasks.py

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
import logging
from .models import (
    AuditLog,
    SystemSetting,
    CacheEntry,
)
from .services import CoreService
from .exceptions import CoreSystemException, AuditLogError
from .utils import get_client_ip # فرض بر این است که این تابع وجود دارد

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def log_audit_event_task(self, user_id: int, action: str, target_model: str, target_id: Any, details: dict, ip_address: str = None, user_agent: str = None):
    """
    Celery task for asynchronously logging audit events.
    This prevents blocking the main request thread for audit logging.
    Implements retry mechanism for transient failures.
    """
    try:
        user = User.objects.get(id=user_id) if user_id else None
        AuditLog.objects.create(
            user=user,
            action=action,
            target_model=target_model,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info(f"Audit event '{action}' for {target_model} ID {target_id} logged asynchronously.")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for audit log task.")
        # اگر کاربر وجود نداشت، ممکن است بخواهید فقط لاگ کنید و خارج شوید، یا خطایی را دوباره بالا بیاورید
        # raise # فقط در صورتی که بخواهید تلاش مجدد داشته باشد
    except Exception as e:
        logger.error(f"Failed to log audit event asynchronously: {str(e)}")
        # Celery retry based on autoretry_for and retry_kwargs
        raise # Re-raise to trigger Celery retry

@shared_task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 2, 'countdown': 30})
def send_generic_notification_task(self, user_id: int, subject: str, template_name: str, context: dict):
    """
    Generic task for sending notification emails asynchronously.
    Can be used for various notifications like alerts, confirmations, etc.
    """
    try:
        user = User.objects.get(id=user_id)
        rendered_context = {**context, 'user': user, 'site_name': getattr(settings, 'SITE_NAME', 'Trading Platform')}

        text_content = render_to_string(f'core/{template_name}.txt', rendered_context)
        html_content = render_to_string(f'core/{template_name}.html', rendered_context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Notification email sent to user {user.email} via task.")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for notification task.")
    except Exception as e:
        logger.error(f"Failed to send notification email task for user id {user_id}: {str(e)}")
        raise # Celery retry

# --- تاسک‌های مرتبط با SystemSetting ---
@shared_task
def refresh_system_settings_cache_task():
    """
    Periodic task (scheduled via Celery Beat) to refresh cached system settings.
    This ensures that settings changes are reflected across all application instances quickly.
    """
    try:
        settings_qs = SystemSetting.objects.filter(is_active=True)
        for setting in settings_qs:
             cache_key = f"system_setting_{setting.key.lower()}"
             cache.set(cache_key, setting.get_parsed_value(), timeout=3600) # 1 hour
        logger.info(f"System settings cache refreshed for {settings_qs.count()} active settings.")
    except Exception as e:
        logger.error(f"Error refreshing system settings cache via task: {str(e)}")
        raise # یا مدیریت خطا مناسب

# --- تاسک‌های مرتبط با Cache ---
@shared_task
def cleanup_expired_cache_entries_task():
    """
    Periodic task (scheduled via Celery Beat) to delete expired CacheEntry objects from the database.
    """
    try:
        deleted_count, _ = CacheEntry.objects.filter(expires_at__lt=timezone.now()).delete()
        logger.info(f"Cleaned up {deleted_count} expired cache entries from the database via task.")
    except Exception as e:
        logger.error(f"Error cleaning up expired cache entries via task: {str(e)}")
        raise # یا مدیریت خطا مناسب

@shared_task
def invalidate_cache_key_task(key: str):
    """
    Task to invalidate (delete) a specific cache key from external cache (e.g., Redis) and DB cache.
    """
    try:
        cache.delete(key)
        CacheEntry.objects.filter(key=key).delete()
        logger.info(f"Cache key '{key}' invalidated via task.")
    except Exception as e:
        logger.error(f"Error invalidating cache key '{key}' via task: {str(e)}")
        # مدیریت خطا مناسب

@shared_task
def bulk_invalidate_cache_keys_task(keys: List[str]):
    """
    Task to invalidate multiple cache keys.
    """
    try:
        if not keys:
            logger.info("Bulk invalidate task called with empty key list.")
            return

        cache.delete_many(keys)
        CacheEntry.objects.filter(key__in=keys).delete()
        logger.info(f"Bulk invalidated {len(keys)} cache keys via task.")
    except Exception as e:
        logger.error(f"Error bulk invalidating cache keys via task: {str(e)}")
        # مدیریت خطا مناسب

# --- تاسک‌های مرتبط با امنیت ---
@shared_task
def process_security_event_task(event_data: Dict[str, Any]):
    """
    Task to process security-related events (e.g., failed login, suspicious IP).
    This can trigger alerts, update reputation scores, or enforce temporary bans.
    """
    try:
        # مثال: ایجاد یک ورودی لاگ حسابرسی برای رویداد امنیتی
        CoreService.log_audit_event(
            user_id=event_data.get('user_id'),
            action=f"SECURITY_{event_data.get('event_type', 'EVENT').upper()}",
            target_model=event_data.get('target_model', 'Generic'),
            target_id=event_data.get('target_id'),
            details=event_data.get('details', {}),
            ip_address=event_data.get('ip_address'),
            user_agent=event_data.get('user_agent')
        )

        # منطق بیشتر: ارسال ایمیل هشدار، ارسال به SIEM، بروزرسانی وضعیت کاربر
        # if event_data['event_type'] == 'failed_login':
        #     increment_failed_attempts_and_lock_if_needed(event_data['user_id'])
        # elif event_data['event_type'] == 'suspicious_ip':
        #     send_suspicious_activity_alert(event_data['user_id'], event_data['ip_address'])

        logger.info(f"Security event '{event_data.get('event_type')}' processed via task.")
    except Exception as e:
        logger.error(f"Error processing security event via task: {str(e)}")
        # مدیریت خطا مناسب، ممکن است نیاز به ارسال هشدار اضطراری باشد

# --- تاسک‌های مرتبط با MAS (اگر نیاز باشد) ---
@shared_task
def broadcast_message_to_agents_task(message_type: str, payload: Dict[str, Any], target_agents_filter: Optional[Dict[str, Any]] = None):
    """
    Task to broadcast a message to multiple agents based on a filter.
    This is a simplified example. A real MAS might use a more sophisticated message bus or pub/sub system.
    """
    try:
        # مثال: پیدا کردن عامل‌هایی که باید پیام را دریافت کنند
        # from apps.agents.models import Agent
        # agents = Agent.objects.all()
        # if target_agents_filter:
        #     agents = agents.filter(**target_agents_filter)

        # for agent in agents:
        #     # ارسال پیام به عامل (مثلاً از طریق یک کانال WebSocket یا ذخیره در یک صف پیام برای عامل)
        #     # agent.receive_message(message_type, payload)
        #     pass # منطق ارسال پیام

        logger.info(f"Broadcast message of type '{message_type}' sent to agents via task.")
    except Exception as e:
        logger.error(f"Error broadcasting message to agents via task: {str(e)}")
        raise # یا مدیریت خطا مناسب

# --- تاسک‌های مرتبط با سرویس ---
# فرض کنید یک متد در CoreService وجود دارد که نیاز به اجرا در پس‌زمینه دارد
@shared_task
def run_core_service_job_task(service_name: str, method_name: str, args: tuple = (), kwargs: dict = None):
    """
    A generic task to run a method from a core service asynchronously.
    This provides flexibility but should be used carefully to avoid passing unserializable objects.
    Args:
        service_name: Name of the service class (e.g., 'CoreService', 'SecurityService').
        method_name: Name of the method to call on the service.
        args: Arguments to pass to the method.
        kwargs: Keyword arguments to pass to the method.
    """
    if kwargs is None:
        kwargs = {}

    try:
        # یافتن کلاس سرویس (نیاز به یک روش ثبت/یا دسترسی مستقیم به کلاس‌ها دارد)
        # این یک مثال کلی است و ممکن است نیاز به پیاده‌سازی پیچیده‌تری داشته باشد
        # service_class = globals()[service_name] # این فقط اگر کلاس در همین فایل باشد
        # service_instance = service_class()
        # method = getattr(service_instance, method_name)
        # method(*args, **kwargs)

        # مثال ساده: اگر فقط یک متد خاص از CoreService نیاز به اجرا در پس‌زمینه داشت
        if service_name == 'CoreService' and method_name == 'some_async_method':
             CoreService.some_async_method(*args, **kwargs)
        else:
             logger.warning(f"Task called for unknown service/method: {service_name}.{method_name}")
             return

        logger.info(f"Service job '{service_name}.{method_name}' executed via task.")
    except AttributeError:
        logger.error(f"Service '{service_name}' or method '{method_name}' not found.")
    except Exception as e:
        logger.error(f"Error executing service job '{service_name}.{method_name}' via task: {str(e)}")
        raise # یا مدیریت خطا مناسب

# --- مثال: تاسک برای پردازش یک ورودی کش جدید ---
@shared_task
def process_new_cache_entry_task(cache_entry_id: int):
    """
    Task to perform additional processing after a new CacheEntry is created.
    e.g., Replicate to other cache nodes, send to external cache service.
    """
    try:
        from .models import CacheEntry
        entry = CacheEntry.objects.get(id=cache_entry_id)
        # منطق پردازش: مثلاً ارسال به یک کش اصلی یا ارسال به یک سرویس خارجی
        # replicate_to_primary_cache(entry.key, entry.value)
        logger.info(f"New cache entry {entry.key} processed via task.")
    except CacheEntry.DoesNotExist:
        logger.error(f"CacheEntry with id {cache_entry_id} does not exist for processing task.")
    except Exception as e:
        logger.error(f"Error processing new cache entry {cache_entry_id} via task: {str(e)}")
        raise # یا مدیریت خطا مناسب

# --- سایر تاسک‌های ممکن ---
# مثلاً تاسک برای بروزرسانی یک شاخص کلیدی، ارسال گزارش دوره‌ای، مدیریت فایل‌های قدیمی و غیره.
