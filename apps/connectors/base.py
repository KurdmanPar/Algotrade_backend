# apps/connectors/base.py
import time
import asyncio
import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import ConnectorLog, RateLimitState, ConnectorSession, ConnectorHealthCheck
from apps.exchanges.models import ExchangeAccount
from apps.logging_app.models import SystemLog # برای لاگ امنیتی
import hashlib
import hmac
import base64


logger = logging.getLogger(__name__)


class ExchangeConnector(ABC):
    """
    کلاس پایه یکپارچه برای تمام کانکتورهای صرافی.
    """
    def __init__(self, api_key: str, api_secret: str, exchange_account_id: int, **kwargs):
        """
        سازنده کلاس برای ذخیره کلیدهای API و اطلاعات حساب.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange_account_id = exchange_account_id
        self.exchange_account = ExchangeAccount.objects.get(id=exchange_account_id)
        self.client = None
        self.session = None
        self.ws_connection = None
        self._rate_limit_lock = asyncio.Lock()

    def _log_interaction(self, action: str, endpoint: str, request_payload: dict, response_payload: dict, status_code: int = None, error_message: str = ""):
        """
        لاگ کردن تعاملات با صرافی.
        """
        correlation_id = request_payload.get('correlation_id', '')
        trace_id = request_payload.get('trace_id', '')
        ConnectorLog.objects.create(
            exchange_account=self.exchange_account,
            level='INFO' if status_code and 200 <= status_code < 300 else 'ERROR',
            action=action,
            endpoint=endpoint,
            request_payload=request_payload,
            response_payload=response_payload,
            status_code=status_code,
            error_message=error_message,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

    def _check_rate_limit(self, endpoint_path: str) -> bool:
        """
        چک کردن محدودیت درخواست.
        """
        now = timezone.now()
        window_start = now.replace(minute=0, second=0, microsecond=0) # 1-minute window

        rate_limit_state, created = RateLimitState.objects.get_or_create(
            exchange_account=self.exchange_account,
            endpoint_path=endpoint_path,
            window_start_at=window_start,
            defaults={'requests_count': 0, 'is_rate_limited': False}
        )

        # به روزرسانی وضعیت قبلی
        if rate_limit_state.window_start_at < now:
            # اگر زمان پنجره گذشته باشد، مقدار جدید بساز
            rate_limit_state.delete()
            rate_limit_state = RateLimitState.objects.create(
                exchange_account=self.exchange_account,
                endpoint_path=endpoint_path,
                window_start_at=window_start,
                requests_count=0,
                is_rate_limited=False
            )

        # پیدا کردن endpoint از مدل
        from .models import ExchangeAPIEndpoint
        try:
            api_endpoint = ExchangeAPIEndpoint.objects.get(exchange=self.exchange_account.exchange, endpoint_path=endpoint_path)
            weight = api_endpoint.rate_limit_weight
        except ExchangeAPIEndpoint.DoesNotExist:
            weight = 1 # وزن پیش‌فرض

        # چک کردن محدودیت
        config = self.exchange_account.exchange.connector_config
        if rate_limit_state.requests_count + weight > config.rate_limit_per_minute:
            rate_limit_state.is_rate_limited = True
            rate_limit_state.retry_after = now + timezone.timedelta(minutes=1)
            rate_limit_state.save()
            return False

        # افزایش تعداد درخواست
        rate_limit_state.requests_count += weight
        rate_limit_state.save()
        return True

    def _handle_rate_limit_wait(self, endpoint_path: str):
        """
        اگر محدودیت شد، صبر کن.
        """
        while not self._check_rate_limit(endpoint_path):
            time.sleep(1)

    def _sign_request(self, message: str) -> str:
        """
        امضای یک پیام بر اساس api_secret (به صورت پیش فرض HMAC-SHA256).
        """
        return base64.b64encode(hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).digest()).decode()

    @abstractmethod
    def connect(self) -> bool:
        """
        اتصال به صرافی.
        """
        pass

    @abstractmethod
    def disconnect(self):
        """
        قطع اتصال از صرافی.
        """
        pass

    @abstractmethod
    def is_connected(self) -> bool:
        """
        چک کردن وضعیت اتصال.
        """
        pass

    @abstractmethod
    def get_balance(self, currency: str = None) -> dict:
        """
        دریافت موجودی.
        """
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, **kwargs):
        """
        ثبت سفارش.
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str, **kwargs):
        """
        لغو سفارش.
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str, **kwargs):
        """
        بررسی وضعیت سفارش.
        """
        pass

    def health_check(self) -> bool:
        """
        بررسی سلامت اتصال.
        """
        try:
            # یک درخواست سبک برای چک کردن اتصال
            account_info = self.get_balance()
            is_healthy = bool(account_info)
            latency = 0 # محاسبه تأخیر
            ConnectorHealthCheck.objects.create(
                exchange_account=self.exchange_account,
                is_healthy=is_healthy,
                latency_ms=latency,
                last_check_at=timezone.now(),
                error_message="" if is_healthy else "Health check failed"
            )
            return is_healthy
        except Exception as e:
            ConnectorHealthCheck.objects.create(
                exchange_account=self.exchange_account,
                is_healthy=False,
                latency_ms=None,
                last_check_at=timezone.now(),
                error_message=str(e)
            )
            SystemLog.objects.create(
                level='ERROR',
                source='ExchangeConnector',
                message=f'Health check failed for {self.exchange_account}: {e}',
                context={'exchange_account_id': self.exchange_account_id}
            )
            return False