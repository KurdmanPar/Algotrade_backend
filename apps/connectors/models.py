# apps/connectors/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class ExchangeConnectorConfig(BaseModel):
    """
    پیکربندی اتصال برای یک صرافی خاص.
    این مدل نحوه اتصال (API Base URL، WebSocket URL، محدودیت‌ها و ...) را ذخیره می‌کند.
    """
    exchange = models.OneToOneField(
        "exchanges.Exchange",  # از اپلیکیشن exchanges
        on_delete=models.CASCADE,
        related_name="connector_config",
        verbose_name=_("Exchange")
    )
    api_base_url = models.URLField(verbose_name=_("API Base URL"))
    ws_base_url = models.URLField(blank=True, verbose_name=_("WebSocket Base URL"))
    sandbox_api_base_url = models.URLField(blank=True, verbose_name=_("Sandbox API Base URL"))
    sandbox_ws_base_url = models.URLField(blank=True, verbose_name=_("Sandbox WebSocket Base URL"))
    rate_limit_per_minute = models.IntegerField(default=1200, verbose_name=_("Rate Limit Per Minute"))
    is_sandbox_mode_default = models.BooleanField(default=False, verbose_name=_("Is Sandbox Mode Default"))
    # اطلاعات احراز هویت پیش‌فرض (اگر نیاز باشد)
    default_credentials_encrypted = models.JSONField(default=dict, blank=True, verbose_name=_("Default Encrypted Credentials (JSON)"))
    # تنظیمات بیشتر مربوط به کانکتور
    config = models.JSONField(default=dict, blank=True, verbose_name=_("Connector Configuration (JSON)"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    def __str__(self):
        return f"Connector Config for {self.exchange.name}"

    class Meta:
        verbose_name = _("Exchange Connector Config")
        verbose_name_plural = _("Exchange Connector Configs")


class APICredential(BaseModel):
    """
    اطلاعات احراز هویت API برای یک حساب صرافی خاص.
    این مدل کلید و سکرت رمزنگاری شده را ذخیره می‌کند.
    """
    exchange_account = models.OneToOneField(
        "exchanges.ExchangeAccount",
        on_delete=models.CASCADE,
        related_name="api_credential",
        verbose_name=_("Exchange Account")
    )
    api_key_encrypted = models.TextField(verbose_name=_("Encrypted API Key"))
    api_secret_encrypted = models.TextField(verbose_name=_("Encrypted API Secret"))
    # IV یا Nonce مورد نیاز برای رمزنگاری (اگر الگوریتم نیاز داشته باشد)
    encrypted_key_iv = models.CharField(max_length=255, blank=True, verbose_name=_("Encryption IV/Nonce"))
    extra_credentials_encrypted = models.JSONField(default=dict, blank=True, verbose_name=_("Extra Encrypted Credentials (JSON)"))
    # امکان غیرفعال کردن موقت این اعتبارنامه
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    last_used_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Used At"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    def __str__(self):
        return f"API Credentials for {self.exchange_account}"

    class Meta:
        verbose_name = _("API Credential")
        verbose_name_plural = _("API Credentials")


class ExchangeAPIEndpoint(BaseModel):
    """
    مدیریت endpointهایی که هر صرافی ارائه می‌دهد.
    """
    exchange = models.ForeignKey("exchanges.Exchange", on_delete=models.CASCADE, related_name="endpoints")
    endpoint_path = models.CharField(max_length=256, verbose_name=_("Endpoint Path")) # e.g., '/api/v3/order'
    method = models.CharField(max_length=10, choices=[('GET', 'GET'), ('POST', 'POST'), ('PUT', 'PUT'), ('DELETE', 'DELETE')])
    is_sandbox_supported = models.BooleanField(default=True)
    rate_limit_weight = models.IntegerField(default=1, verbose_name=_("Weight for Rate Limiter"))
    description = models.TextField(blank=True)

    class Meta:
        unique_together = ("exchange", "endpoint_path", "method")
        verbose_name = _("Exchange API Endpoint")
        verbose_name_plural = _("Exchange API Endpoints")


class ConnectorSession(BaseModel):
    """
    نگهداری نشست‌های اتصال (WebSocket یا REST).
    """
    SESSION_TYPE_CHOICES = [
        ('WEBSOCKET', _('WebSocket')),
        ('REST', _('REST Session')),
        ('STREAM', _('Data Stream')),
    ]
    exchange_account = models.ForeignKey("exchanges.ExchangeAccount", on_delete=models.CASCADE, related_name="sessions")
    session_id = models.CharField(max_length=128, verbose_name=_("Session ID")) # e.g., WS connection ID
    session_type = models.CharField(max_length=16, choices=SESSION_TYPE_CHOICES, verbose_name=_("Session Type"))
    status = models.CharField(max_length=16, choices=[('ACTIVE', 'Active'), ('INACTIVE', 'Inactive'), ('ERROR', 'Error')])
    connected_at = models.DateTimeField()
    disconnected_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True)

    class Meta:
        unique_together = ("exchange_account", "session_id")
        verbose_name = _("Connector Session")
        verbose_name_plural = _("Connector Sessions")


class RateLimitState(BaseModel):
    """
    مدیریت دقیق محدودیت‌های صرافی.
    """
    exchange_account = models.ForeignKey("exchanges.ExchangeAccount", on_delete=models.CASCADE, related_name="rate_limits")
    endpoint_path = models.CharField(max_length=256) # e.g., '/api/v3/order'
    window_start_at = models.DateTimeField()
    requests_count = models.IntegerField(default=0)
    is_rate_limited = models.BooleanField(default=False)
    retry_after = models.DateTimeField(null=True, blank=True) # زمانی که می‌توان دوباره امتحان کرد

    class Meta:
        verbose_name = _("Rate Limit State")
        verbose_name_plural = _("Rate Limit States")


class ConnectorLog(BaseModel):
    """
    لاگ کردن تمام درخواست‌ها و پاسخ‌های ارسالی/دریافتی از صرافی.
    """
    LOG_LEVEL_CHOICES = [
        ("DEBUG", _("Debug")),
        ("INFO", _("Info")),
        ("WARNING", _("Warning")),
        ("ERROR", _("Error")),
        ("CRITICAL", _("Critical")),
    ]
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.CASCADE,
        related_name="connector_logs",
        verbose_name=_("Exchange Account")
    )
    level = models.CharField(max_length=16, choices=LOG_LEVEL_CHOICES, verbose_name=_("Log Level"))
    action = models.CharField(max_length=128, verbose_name=_("Action"))  # e.g., 'place_order', 'get_balance', 'connect'
    endpoint = models.CharField(max_length=256, verbose_name=_("Endpoint"))  # e.g., '/api/v3/order'
    request_payload = models.JSONField(default=dict, blank=True, verbose_name=_("Request Payload (JSON)"))
    response_payload = models.JSONField(default=dict, blank=True, verbose_name=_("Response Payload (JSON)"))
    status_code = models.IntegerField(null=True, blank=True, verbose_name=_("Status Code"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))
    # اطلاعات بیشتر برای ردیابی
    correlation_id = models.CharField(max_length=128, blank=True, verbose_name=_("Correlation ID"))
    trace_id = models.CharField(max_length=128, blank=True, verbose_name=_("Trace ID"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Connector Log")
        verbose_name_plural = _("Connector Logs")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['exchange_account', '-created_at']), # برای نمایش معکوس تاریخچه
            models.Index(fields=['correlation_id']), # برای ردیابی لاگ‌های مرتبط
        ]

    def __str__(self):
        return f"[{self.level}] {self.action} on {self.exchange_account} - {self.status_code or 'N/A'}"


class ConnectorHealthCheck(BaseModel):
    """
    نگهداری نتایج بررسی سلامت اتصال به صرافی.
    """
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.CASCADE,
        related_name="health_checks",
        verbose_name=_("Exchange Account")
    )
    is_healthy = models.BooleanField(verbose_name=_("Is Healthy"))
    latency_ms = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True, verbose_name=_("Latency (ms)"))
    last_check_at = models.DateTimeField(verbose_name=_("Last Check At"))
    error_message = models.TextField(blank=True, verbose_name=_("Error Message"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    class Meta:
        verbose_name = _("Connector Health Check")
        verbose_name_plural = _("Connector Health Checks")
        ordering = ['-last_check_at']
        indexes = [
            models.Index(fields=['exchange_account', '-last_check_at']), # برای نمایش معکوس تاریخچه
        ]

    def __str__(self):
        status = "Healthy" if self.is_healthy else "Unhealthy"
        return f"{self.exchange_account} - {status} at {self.last_check_at}"