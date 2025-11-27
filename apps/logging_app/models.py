# apps/logging_app/models.py
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel  # ارث‌بری از BaseModel برای فیلدهای timestamp


class SystemLog(BaseModel):
    """
    برای ثبت لاگ‌های سیستمی، خطاها و رویدادهای مهم سرور.
    """
    LEVEL_CHOICES = [
        ("DEBUG", "Debug"),
        ("INFO", "Info"),
        ("WARNING", "Warning"),
        ("ERROR", "Error"),
        ("CRITICAL", "Critical"),
    ]
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default="INFO")
    source = models.CharField(max_length=128, help_text="e.g., 'RiskAgent', 'ExecutionAgent', 'Django.Views'")
    message = models.TextField()

    # لینک به مدل‌های دیگر برای ردیابی بهتر (اختیاری)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                             related_name="system_logs")
    bot = models.ForeignKey("bots.Bot", on_delete=models.SET_NULL, null=True, blank=True, related_name="system_logs")

    # داده‌های ساختاریافته برای اطلاعات بیشتر
    context = models.JSONField(default=dict, blank=True, help_text="e.g., {'order_id': 123, 'error_code': 'E101'}")

    def __str__(self):
        return f"[{self.level}] {self.source}: {self.message[:50]}"

class NotificationChannel(BaseModel):
    """
    برای تعریف کانال‌های مختلف ارسال اطلاعیه (ایمیل، SMS، تلگرام و...).
    این مدل باعث می‌شود سیستم بسیار انعطاف‌پذیر باشد.
    """
    name = models.CharField(max_length=64, unique=True)  # e.g., 'Email', 'Telegram', 'SMS'
    code = models.CharField(max_length=32, unique=True)  # e.g., 'EMAIL', 'TELEGRAM', 'SMS'
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # برای نگهداری تنظیمات هر کانال (مثل API Key تلگرام، توکن سرویس SMS و...)
    config = models.JSONField(default=dict, blank=True, help_text="e.g., {'api_key': '...', 'bot_token': '...'}")

    def __str__(self):
        return self.name


class Alert(BaseModel):
    """
    مدل اصلی برای ثبت هشدارها و لاگ‌های مهم سیستم.
    هر هشدار می‌تواند به یک یا چند کانال ارسال شود.
    """
    # لینک به کاربر، بات، سفارش یا پوزیشن مرتبط
    # استفاده از settings.AUTH_USER_MODEL بهترین روش برای ارجاع به مدل کاربر سفارشی است
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="alerts", null=True,
                             blank=True)
    bot = models.ForeignKey("bots.Bot", on_delete=models.CASCADE, related_name="alerts", null=True, blank=True)
    order = models.ForeignKey("trading.Order", on_delete=models.CASCADE, related_name="alerts", null=True, blank=True)
    position = models.ForeignKey("trading.Position", on_delete=models.CASCADE, related_name="alerts", null=True,
                                 blank=True)

    # نوع و سطح اهمیت هشدار
    ALERT_TYPE_CHOICES = [
        ("INFO", "Information"),
        ("SUCCESS", "Success"),  # مثلاً سفارش با موفقیت انجام شد
        ("WARNING", "Warning"),  # مثلاً حدضرر نزدیک است
        ("ERROR", "Error"),  # مثلاً خطا در اتصال به صرافی
        ("CRITICAL", "Critical"),  # مثلاً ریسک کل پرتفوی بالا رفته
    ]
    type = models.CharField(max_length=32, choices=ALERT_TYPE_CHOICES, default="INFO")

    title = models.CharField(max_length=256)
    message = models.TextField()

    # وضعیت ارسال هشدار
    STATUS_CHOICES = [
        ("PENDING", "Pending"),  # در صف ارسال
        ("SENT", "Sent"),  # ارسال شد
        ("FAILED", "Failed"),  # ارسال با شکست مواجه شد
    ]
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")

    # کانال‌هایی که هشدار به آن‌ها ارسال شده است
    # ManyToManyField به مدل NotificationChannel که در همین اپلیکیشن تعریف شده است
    channels_sent = models.ManyToManyField("logging_app.NotificationChannel", related_name="sent_alerts", blank=True)

    # اطلاعات اضافی به صورت ساختاریافته
    payload = models.JSONField(default=dict, blank=True, help_text="e.g., {'order_id': 123, 'price': 45000}")

    def __str__(self):
        # نمایش نام کاربر یا 'System' اگر کاربری وجود نداشت
        target = self.user.email if self.user else 'System'
        return f"{self.type}: {self.title} for {target}"


class UserNotificationPreference(BaseModel):
    """
    برای اینکه هر کاربر بتواند مشخص کند کدام نوع هشدار را از کدام کانال دریافت کند.
    این برای تجربه کاربری و جلوگیری از اسپم بسیار حیاتی است.
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="notification_preferences")

    # به کدام نوع هشدار مربوط است (مثلاً 'ORDER_FILLED', 'RISK_WARNING')
    alert_type = models.CharField(max_length=64, help_text="e.g., 'ORDER_FILLED'")

    channel = models.ForeignKey("logging_app.NotificationChannel", on_delete=models.CASCADE,
                                related_name="user_preferences")

    is_enabled = models.BooleanField(default=True,
                                     help_text="If user wants to receive this alert type on this channel.")

    class Meta:
        unique_together = ("user", "alert_type", "channel")

    def __str__(self):
        return f"{self.user.email} - {self.alert_type} via {self.channel.name}"