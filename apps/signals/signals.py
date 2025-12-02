# apps/signals/signals.py
"""
Event handlers و audit trail برای مدل‌های سیگنال
این فایل توسط apps.signals.apps.SignalsConfig.ready() لود می‌شود
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.utils import timezone
from .models import Signal, SignalLog, SignalAlert
import logging

logger = logging.getLogger(__name__)


# ============================================
# Audit Trail برای سیگنال‌ها
# ============================================

@receiver(pre_save, sender=Signal)
def capture_old_status(sender, instance, **kwargs):
    """ذخیره وضعیت قبلی قبل از تغییر"""
    if instance.pk:
        try:
            old_instance = Signal.objects.get(pk=instance.pk)
            instance._old_status = old_instance.status
        except Signal.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender=Signal)
def log_signal_status_change(sender, instance, created, **kwargs):
    """لاگ خودکار تغییرات وضعیت سیگنال"""
    if not created and hasattr(instance, '_old_status') and instance._old_status != instance.status:
        SignalLog.objects.create(
            signal=instance,
            old_status=instance._old_status,
            new_status=instance.status,
            message=f"Automatic status transition: {instance._old_status} → {instance.status}",
            changed_by_agent=None,  # یا instance._changed_by_agent اگر set شده باشد
            changed_by_user=getattr(instance, '_changed_by_user', None)
        )
        logger.info(
            f"Signal#{instance.id} status changed: {instance._old_status} → {instance.status}"
        )


# ============================================
# لاگینگ امن برای ادمین
# ============================================

@receiver(user_logged_in)
def log_admin_login(sender, request, user, **kwargs):
    """لاگ ورود به پنل ادمین - برای ردیابی دسترسی‌ها"""
    ip = request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0] or request.META.get('REMOTE_ADDR')
    logger.warning(f"ADMIN LOGIN: User#{user.id} ({user.username}) from IP {ip}")


@receiver(user_logged_out)
def log_admin_logout(sender, request, user, **kwargs):
    """لاگ خروج از پنل ادمین"""
    logger.warning(f"ADMIN LOGOUT: User#{user.id} ({user.username})")


# ============================================
# هشدار برای سیگنال‌های بحرانی
# ============================================

@receiver(post_save, sender=SignalAlert)
def notify_critical_alert(sender, instance, created, **kwargs):
    """ارسال نوتیفیکیشن برای هشدارهای بحرانی"""
    if created and instance.severity >= 3:  # HIGH or CRITICAL
        logger.critical(
            f"CRITICAL ALERT: Signal#{instance.signal_id} - {instance.title}"
        )