# apps/signals/models.py
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel  # ارث‌بری از BaseModel برای فیلدهای زمانی
from apps.logging_app.models import SystemLog

class Signal(BaseModel):
    """
    برای ثبت سیگنال‌های تولید شده توسط استراتژی‌ها یا عامل‌های هوشمند.
    این سیگنال‌ها قبل از تبدیل به سفارش، توسط عامل ریسک و مدیریت ریسک بررسی می‌شوند.
    """
    DIRECTION_CHOICES = [
        ("BUY", "Buy"),
        ("SELL", "Sell"),
        ("CLOSE_LONG", "Close Long"),
        ("CLOSE_SHORT", "Close Short"),
    ]
    SIGNAL_TYPE_CHOICES = [
        ("ENTRY", "Entry Signal"),
        ("EXIT", "Exit Signal"),
        ("TAKE_PROFIT", "Take Profit"),
        ("STOP_LOSS", "Stop Loss"),
        ("SCALE_IN", "Scale In"),
        ("SCALE_OUT", "Scale Out"),
    ]
    STATUS_CHOICES = [
        ("PENDING", "Pending"),
        ("APPROVED", "Approved by Risk"),
        ("REJECTED", "Rejected by Risk"),
        ("EXECUTED", "Executed"),
        ("EXPIRED", "Expired"),
    ]

    # لینک به استراتژی و نسخه‌ای که سیگنال را تولید کرده است
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="signals",
        help_text="The strategy version that generated this signal."
    )

    # لینک به بات و کاربر مالک سیگنال
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="signals",
        null=True,
        blank=True,
        help_text="The bot this signal is associated with."
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="signals"
    )

    # اطلاعات اصلی سیگنال
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="signals"
    )
    direction = models.CharField(max_length=16, choices=DIRECTION_CHOICES)
    signal_type = models.CharField(max_length=16, choices=SIGNAL_TYPE_CHOICES, default="ENTRY")

    # اطلاعات تکمیلی سیگنال
    price = models.DecimalField(max_digits=32, decimal_places=16, null=True, blank=True,
                                help_text="Suggested price for limit orders.")
    quantity = models.DecimalField(max_digits=32, decimal_places=16, help_text="Suggested quantity.")
    confidence_score = models.FloatField(default=0.0, help_text="Confidence of the signal from 0.0 to 1.0")
    payload = models.JSONField(default=dict, blank=True, help_text="Additional data like indicators, AI scores, etc.")

    # وضعیت و زمان‌بندی
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="PENDING")
    final_order = models.OneToOneField(
        "trading.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_signal"
    )

    # زمان‌بندی
    generated_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Signal is invalid after this time.")
    processed_at = models.DateTimeField(null=True, blank=True,
                                        help_text="Time when signal was processed by risk agent.")

    # لینک به لاگ سیستمی برای ردیابی کامل (بسیار مهم)
    related_log_entry = models.ForeignKey(
        "logging_app.SystemLog",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="caused_signals",
        help_text="Links to a system log entry if this signal's processing caused an event."
    )

    def __str__(self):
        return f"{self.direction} {self.quantity} {self.instrument.symbol} ({self.status})"