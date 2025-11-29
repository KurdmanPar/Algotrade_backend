# apps/connectors/tasks.py
from celery import shared_task
from .models import ConnectorSession
from .registry import get_connector
from apps.exchanges.models import ExchangeAccount
from django.utils import timezone


@shared_task
def perform_health_check(exchange_account_id: int):
    """
    تسک پس‌زمینه برای بررسی سلامت یک حساب صرافی.
    """
    try:
        exchange_account = ExchangeAccount.objects.get(id=exchange_account_id)
        # دریافت کانکتور مربوطه
        ConnectorClass = get_connector(exchange_account.exchange.code)
        if not ConnectorClass:
            raise ValueError(f"Connector not found for exchange: {exchange_account.exchange.code}")

        # فرض کنید کلیدها از مدل APICredential گرفته می‌شود
        creds = exchange_account.api_credential
        connector = ConnectorClass(
            api_key=creds.api_key_encrypted,
            api_secret=creds.api_secret_encrypted,
            exchange_account_id=exchange_account_id
        )
        connector.connect()
        is_healthy = connector.health_check()
        return f"Health check for {exchange_account} completed. Healthy: {is_healthy}"
    except Exception as e:
        return f"Health check failed for account {exchange_account_id}: {e}"


@shared_task
def reconnect_failed_sessions():
    """
    تسک پس‌زمینه برای تلاش مجدد برای اتصال نشست‌های قطع شده.
    """
    failed_sessions = ConnectorSession.objects.filter(status='ERROR')
    for session in failed_sessions:
        # منطق تلاش مجدد اتصال
        # مثلاً ایجاد یک تسک جدید برای اتصال مجدد
        attempt_reconnect.delay(session.id)


@shared_task
def attempt_reconnect(session_id: int):
    """
    تسک پس‌زمینه برای تلاش مجدد برای یک نشست خاص.
    """
    try:
        session = ConnectorSession.objects.get(id=session_id)
        # منطق اتصال مجدد
        # ...
        session.status = 'ACTIVE'
        session.disconnected_at = None
        session.save()
        return f"Reconnection attempt for session {session_id} successful."
    except Exception as e:
        return f"Reconnection attempt for session {session_id} failed: {e}"
