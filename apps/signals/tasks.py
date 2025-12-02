# apps/signals/tasks.py
from celery import shared_task
from django.utils import timezone
from .models import Signal, SignalStatus

@shared_task(bind=True, max_retries=3)
def process_expired_signals(self):
    """تسک پس‌زمینه برای منقضی کردن سیگنال‌ها"""
    expired_signals = Signal.objects.filter(
        status__in=[SignalStatus.PENDING, SignalStatus.SENT_TO_RISK],
        expires_at__lte=timezone.now()
    )
    count = expired_signals.update(status=SignalStatus.EXPIRED)
    logger.info(f"{count} signals expired by background task")
    return count

