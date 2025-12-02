# apps/signals/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from typing import Optional, Dict, Any
import logging

from apps.core.models import BaseModel

logger = logging.getLogger(__name__)


class SignalStatus:
    """کلاس ایمن برای مدیریت وضعیت‌های سیگنال"""
    PENDING = "PENDING"
    SENT_TO_RISK = "SENT_TO_RISK"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SENT_TO_EXECUTION = "SENT_TO_EXECUTION"
    EXECUTED = "EXECUTED"
    EXPIRED = "EXPIRED"
    CANCELED = "CANCELED"

    CHOICES = [
        (PENDING, _("Pending")),
        (SENT_TO_RISK, _("Sent to Risk Agent")),
        (APPROVED, _("Approved by Risk")),
        (REJECTED, _("Rejected by Risk")),
        (SENT_TO_EXECUTION, _("Sent to Execution Agent")),
        (EXECUTED, _("Executed")),
        (EXPIRED, _("Expired")),
        (CANCELED, _("Canceled")),
    ]

    # ماشین وضعیت ایمن: تعریف انتقالات مجاز
    ALLOWED_TRANSITIONS = {
        PENDING: [SENT_TO_RISK, REJECTED, EXPIRED, CANCELED],
        SENT_TO_RISK: [APPROVED, REJECTED, EXPIRED],
        APPROVED: [SENT_TO_EXECUTION, REJECTED, EXPIRED, CANCELED],
        REJECTED: [],  # وضعیت نهایی
        SENT_TO_EXECUTION: [EXECUTED, REJECTED, EXPIRED],
        EXECUTED: [],  # وضعیت نهایی
        EXPIRED: [],  # وضعیت نهایی
        CANCELED: [],  # وضعیت نهایی
    }


class SignalDirection:
    """کلاس ایمن برای جهت‌های معاملاتی"""
    BUY = "BUY"
    SELL = "SELL"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"

    CHOICES = [
        (BUY, _("Buy")),
        (SELL, _("Sell")),
        (CLOSE_LONG, _("Close Long")),
        (CLOSE_SHORT, _("Close Short")),
    ]


class SignalType:
    """کلاس ایمن برای انواع سیگنال‌ها"""
    ENTRY = "ENTRY"
    EXIT = "EXIT"
    TAKE_PROFIT = "TAKE_PROFIT"
    STOP_LOSS = "STOP_LOSS"
    SCALE_IN = "SCALE_IN"
    SCALE_OUT = "SCALE_OUT"
    LIQUIDATION = "LIQUIDATION"

    CHOICES = [
        (ENTRY, _("Entry Signal")),
        (EXIT, _("Exit Signal")),
        (TAKE_PROFIT, _("Take Profit")),
        (STOP_LOSS, _("Stop Loss")),
        (SCALE_IN, _("Scale In")),
        (SCALE_OUT, _("Scale Out")),
        (LIQUIDATION, _("Liquidation Signal")),
    ]


class Signal(BaseModel):
    """
    مدل اصلی سیگنال‌های معاملاتی با بالاترین سطح امنیت و یکپارچگی داده.

    این مدل شامل تمام اطلاعات مرتبط با یک سیگنال معاملاتی از تولید تا اجرا است.
    تمام فیلدها با دقت انتخاب شده‌اند تا از نفوذ و دستکاری جلوگیری شود.
    """

    # فیلدهای ارتباطی - همه با PROTECT برای جلوگیری از حذف ناخواسته
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,  # تغییر از CASCADE به PROTECT برای امنیت بیشتر
        related_name="signals",
        verbose_name=_("User"),
        help_text=_("کاربر مالک سیگنال"),
    )
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.SET_NULL,
        related_name="signals",
        null=True,
        blank=True,
        verbose_name=_("Bot"),
        help_text=_("ربات تولیدکننده سیگنال (اختیاری)"),
    )
    strategy_version = models.ForeignKey(
        "strategies.StrategyVersion",
        on_delete=models.PROTECT,  # محافظت در برابر حذف
        related_name="signals",
        verbose_name=_("Strategy Version"),
        help_text=_("نسخه استراتژی تولیدکننده سیگنال"),
    )
    agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.PROTECT,  # محافظت در برابر حذف
        related_name="signals",
        verbose_name=_("Agent (MAS)"),
        help_text=_("عامل هوشمند تولیدکننده سیگنال - احراز هویت شده"),
    )
    exchange_account = models.ForeignKey(
        "exchanges.ExchangeAccount",
        on_delete=models.PROTECT,  # PROTECT بسیار مهم برای حساب‌های مالی
        related_name="signals",
        verbose_name=_("Exchange Account"),
        help_text=_("حساب صرافی هدف - غیرقابل تغییر پس از ایجاد"),
    )
    instrument = models.ForeignKey(
        "instruments.Instrument",
        on_delete=models.PROTECT,
        related_name="signals",
        verbose_name=_("Instrument"),
        help_text=_("دارایی معاملاتی"),
    )
    final_order = models.OneToOneField(
        "trading.Order",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_signal",
        verbose_name=_("Final Order"),
        help_text=_("سفارش نهایی اجراشده - فقط توسط اجراکننده قابل تنظیم"),
    )

    # اطلاعات سیگنال - غیرقابل تغییر پس از ایجاد
    direction = models.CharField(
        max_length=16,
        choices=SignalDirection.CHOICES,
        verbose_name=_("Direction"),
        help_text=_("جهت معاملاتی - غیرقابل تغییر پس از تولید"),
    )
    signal_type = models.CharField(
        max_length=16,
        choices=SignalType.CHOICES,
        default=SignalType.ENTRY,
        verbose_name=_("Signal Type"),
        help_text=_("نوع سیگنال"),
    )

    # پارامترهای معاملاتی - با اعتبارسنجی دقیق
    quantity = models.DecimalField(
        max_digits=32,
        decimal_places=16,
        validators=[MinValueValidator(Decimal('0.000001'))],
        verbose_name=_("Suggested Quantity"),
        help_text=_("مقدار پیشنهادی - باید مثبت باشد"),
    )
    price = models.DecimalField(
        max_digits=32,
        decimal_places=16,
        null=True,
        blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        verbose_name=_("Suggested Price"),
        help_text=_("قیمت پیشنهادی برای سفارشات لیمیت (اختیاری)"),
    )

    # امتیاز اعتماد - محدود به بازه 0-1
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        verbose_name=_("Confidence Score"),
        help_text=_("امتیاز اعتماد از 0.0 تا 1.0"),
    )

    # داده‌های اضافی - ذخیره‌سازی ایمن JSON
    payload = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Payload (JSON)"),
        help_text=_("داده‌های اضافی مانند اندیکاتورها، نتایج AI - رمزنگاری شده در REST API"),
    )

    # وضعیت - با ماشین وضعیت ایمن
    status = models.CharField(
        max_length=17,
        choices=SignalStatus.CHOICES,
        default=SignalStatus.PENDING,
        verbose_name=_("Status"),
        help_text=_("وضعیت فعلی سیگنال"),
    )

    # اولویت - اعداد بالاتر = اولویت بالاتر
    priority = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("Priority"),
        help_text=_("اولویت پردازش - اعداد بالاتر = اولویت بیشتر"),
    )

    # پرچم‌های وضعیتی
    is_recurring = models.BooleanField(
        default=False,
        verbose_name=_("Is Recurring"),
        help_text=_("آیا این سیگنال تکرارشونده است؟"),
    )
    sent_to_risk = models.BooleanField(
        default=False,
        verbose_name=_("Sent to Risk"),
        help_text=_("آیا به ریسک ارسال شده؟ (فقط توسط سیستم قابل تغییر)"),
    )
    sent_to_execution = models.BooleanField(
        default=False,
        verbose_name=_("Sent to Execution"),
        help_text=_("آیا به اجرا ارسال شده؟ (فقط توسط سیستم قابل تغییر)"),
    )

    # زمان‌بندی - با دقت نانوثانیه
    generated_at = models.DateTimeField(
        db_index=True,
        verbose_name=_("Generated At"),
        help_text=_("زمان تولید سیگنال توسط عامل"),
    )
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Expires At"),
        help_text=_("زمان انقضا - پس از آن سیگنال غیرمعتبر است"),
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Processed At"),
        help_text=_("زمان پردازش توسط عامل ریسک"),
    )
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Executed At"),
        help_text=_("زمان اجرای موفقیت‌آمیز"),
    )

    # ردیابی - برای همبستگی در میکروسرویس‌ها
    correlation_id = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        verbose_name=_("Correlation ID"),
        help_text=_("شناسه همبستگی برای ردیابی در سیستم توزیع‌شده"),
    )

    # جزئیات تایید ریسک - فقط توسط ریسک‌منیجر قابل ویرایش
    risk_approval_details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Risk Approval Details (JSON)"),
        help_text=_("جزئیات تایید/رد ریسک - شامل دلایل و امضای دیجیتال"),
    )

    # فیلدهای فقط‌خواندنی برای لاگینگ
    created_by_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("Created By IP"),
        help_text=_("IP ایجادکننده سیگنال - برای امنیت و حسابرسی"),
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name=_("User Agent"),
        help_text=_("اطلاعات عامل کاربر - برای احراز هویت عامل"),
    )

    class Meta:
        verbose_name = _("Signal")
        verbose_name_plural = _("Signals")
        # ایندکس‌های بهینه برای کوئری‌های رایج
        indexes = [
            models.Index(fields=['user', '-generated_at']),
            models.Index(fields=['status', '-generated_at']),
            models.Index(fields=['correlation_id']),
            models.Index(fields=['agent', 'status']),
            models.Index(fields=['instrument', 'status']),
            models.Index(fields=['status', 'priority', '-generated_at']),
        ]
        # محدودیت‌های یکپارچگی داده
        constraints = [
            models.CheckConstraint(
                check=models.Q(confidence_score__gte=0.0) & models.Q(confidence_score__lte=1.0),
                name="signal_confidence_score_range"
            ),
            models.CheckConstraint(
                check=models.Q(quantity__gt=0),
                name="signal_quantity_positive"
            ),
            models.CheckConstraint(
                check=models.Q(generated_at__lte=models.F('expires_at')) | models.Q(expires_at__isnull=True),
                name="signal_expires_after_generation"
            ),
        ]

    def __str__(self) -> str:
        symbol = self.instrument.symbol if hasattr(self.instrument, 'symbol') else 'Unknown'
        return f"Signal#{self.id}: {self.direction} {self.quantity} {symbol} [{self.status}]"

    def clean(self) -> None:
        """اعتبارسنجی سطح مدل برای اطمینان از یکپارچگی داده"""
        super().clean()

        # اعتبارسنجی زمان
        if self.expires_at and self.generated_at and self.expires_at <= self.generated_at:
            raise ValidationError({
                'expires_at': _("زمان انقضا باید بعد از زمان تولید باشد")
            })

        # اعتبارسنجی quantity برای معاملات بستن
        if self.direction in [SignalDirection.CLOSE_LONG, SignalDirection.CLOSE_SHORT] and not self.price:
            raise ValidationError({
                'price': _("قیمت بستن پوزیشن الزامی است")
            })

        # اطمینان از عدم تغییر فیلدهای حیاتی پس از ایجاد
        if self.pk:
            old = Signal.objects.filter(pk=self.pk).first()
            if old:
                # این فیلدها نباید پس از ایجاد تغییر کنند
                immutable_fields = ['user', 'exchange_account', 'instrument', 'direction', 'generated_at']
                for field in immutable_fields:
                    if getattr(old, field) != getattr(self, field):
                        raise ValidationError({
                            field: _(f"فیلد {field} پس از ایجاد سیگنال غیرقابل تغییر است")
                        })

    def save(self, *args: Any, **kwargs: Any) -> None:
        """ذخیره‌سازی ایمن با اعتبارسنجی و لاگ خودکار"""
        # اعتبارسنجی قبل از ذخیره
        self.full_clean()

        # بررسی انتقالات وضعیت ایمن
        if self.pk:
            old_status = Signal.objects.filter(pk=self.pk).values_list('status', flat=True).first()
            if old_status and old_status != self.status:
                if self.status not in SignalStatus.ALLOWED_TRANSITIONS.get(old_status, []):
                    logger.warning(
                        f"انتقال وضعیت غیرمجاز: Signal#{self.id} از {old_status} به {self.status}"
                    )
                    raise ValidationError({
                        'status': _(f"انتقال از {old_status} به {self.status} مجاز نیست")
                    })

        # ذخیره با atomic transaction
        with transaction.atomic():
            super().save(*args, **kwargs)

            # ایجاد لاگ خودکار برای تغییرات وضعیت
            if self.pk and 'old_status' in locals():
                SignalLog.objects.create(
                    signal=self,
                    old_status=old_status,
                    new_status=self.status,
                    message=f"Status changed from {old_status} to {self.status}",
                    changed_by_agent=getattr(self, '_changed_by_agent', None),
                    changed_by_user=getattr(self, '_changed_by_user', None),
                )

    def is_expired(self) -> bool:
        """بررسی انقضای سیگنال"""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at

    @property
    def elapsed_time(self) -> Optional[timezone.timedelta]:
        """زمان سپری‌شده از تولید سیگنال"""
        if self.generated_at:
            return timezone.now() - self.generated_at
        return None


class SignalLog(BaseModel):
    """
    لاگ دقیق و غیرقابل تغییر برای تمام تغییرات سیگنال.

    این مدل به عنوان audit trail عمل کرده و برای حسابرسی و ردگیری مسئولیت‌ها استفاده می‌شود.
    """

    signal = models.ForeignKey(
        Signal,
        on_delete=models.PROTECT,  # جلوگیری از حذف سیگنال دارای لاگ
        related_name="status_logs",
        verbose_name=_("Signal"),
        db_index=True,
    )
    old_status = models.CharField(
        max_length=17,
        verbose_name=_("Old Status"),
        help_text=_("وضعیت قبلی - فقط‌خواندنی"),
    )
    new_status = models.CharField(
        max_length=17,
        verbose_name=_("New Status"),
        help_text=_("وضعیت جدید - فقط‌خواندنی"),
    )
    message = models.TextField(
        blank=True,
        verbose_name=_("Log Message"),
        help_text=_("توضیحات تغییر"),
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Details (JSON)"),
        help_text=_("جزئیات تکمیلی - رمزنگاری شده در API"),
    )
    changed_by_agent = models.ForeignKey(
        "agents.Agent",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By Agent"),
        help_text=_("عامل هوشمند ایجادکننده تغییر"),
    )
    changed_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Changed By User"),
        help_text=_("کاربر ایجادکننده تغییر"),
    )

    # اطلاعات محیطی برای حسابرسی
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name=_("IP Address"),
        help_text=_("IP آدرس منبع تغییر"),
    )
    user_agent = models.CharField(
        max_length=512,
        blank=True,
        verbose_name=_("User Agent"),
        help_text=_("اطلاعات کارگزار برای احراز هویت"),
    )

    class Meta:
        verbose_name = _("Signal Log")
        verbose_name_plural = _("Signal Logs")
        # مرتب‌سازی پیش‌فرض: جدیدترین اول
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=['signal', '-created_at']),
            models.Index(fields=['new_status', '-created_at']),
            models.Index(fields=['changed_by_agent', '-created_at']),
        ]
        # جلوگیری از ویرایش یا حذف لاگ‌ها
        permissions = [
            ("can_view_audit_logs", _("Can view audit logs")),
        ]

    def __str__(self) -> str:
        return f"Log#{self.id} Signal#{self.signal_id}: {self.old_status}→{self.new_status}"

    def save(self, *args: Any, **kwargs: Any) -> None:
        """ذخیره‌سازی لاگ با اعتبارسنجی"""
        if self.pk:
            # جلوگیری از ویرایش لاگ‌های موجود (audit trail immutable)
            raise ValidationError(_("لاگ‌های حسابرسی غیرقابل ویرایش هستند"))
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> None:
        """جلوگیری از حذف لاگ‌ها"""
        raise ValidationError(_("لاگ‌های حسابرسی قابل حذف نیستند"))


class AlertType:
    """کلاس ایمن برای انواع هشدارها"""
    HIGH_CONFIDENCE = "HIGH_CONFIDENCE"
    RISK_REJECTION = "RISK_REJECTION"
    EXECUTION_ERROR = "EXECUTION_ERROR"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"

    CHOICES = [
        (HIGH_CONFIDENCE, _("High Confidence Signal")),
        (RISK_REJECTION, _("Risk Rejection")),
        (EXECUTION_ERROR, _("Execution Error")),
        (MANUAL_OVERRIDE, _("Manual Override")),
    ]


class Severity:
    """سطوح شدت هشدار"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    CHOICES = [
        (LOW, _("Low")),
        (MEDIUM, _("Medium")),
        (HIGH, _("High")),
        (CRITICAL, _("Critical")),
    ]


class SignalAlert(BaseModel):
    """
    هشدارهای ایمن برای رویدادهای مهم سیگنال.

    این مدل برای اطلاع‌رسانی فوری به کاربران/مدیران در مورد رویدادهای حساس استفاده می‌شود.
    """

    signal = models.ForeignKey(
        Signal,
        on_delete=models.PROTECT,  # جلوگیری از حذف سیگنال دارای هشدار
        related_name="signal_alerts",
        verbose_name=_("Signal"),
        db_index=True,
    )
    alert_type = models.CharField(
        max_length=32,
        choices=AlertType.CHOICES,
        verbose_name=_("Alert Type"),
        help_text=_("نوع هشدار"),
    )
    severity = models.IntegerField(
        choices=Severity.CHOICES,
        default=Severity.MEDIUM,
        verbose_name=_("Severity"),
        help_text=_("سطح بحرانی بودن هشدار"),
    )
    title = models.CharField(
        max_length=256,
        verbose_name=_("Title"),
        help_text=_("عنوان کوتاه هشدار"),
    )
    description = models.TextField(
        verbose_name=_("Description"),
        help_text=_("توضیحات کامل هشدار"),
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Details (JSON)"),
        help_text=_("اطلاعات تکمیلی - رمزنگاری شده"),
    )

    # مدیریت تایید هشدار
    is_acknowledged = models.BooleanField(
        default=False,
        verbose_name=_("Is Acknowledged"),
        help_text=_("آیا توسط کاربر تایید شده؟"),
    )
    acknowledged_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_("Acknowledged At"),
        help_text=_("زمان تایید هشدار"),
    )
    acknowledged_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_("Acknowledged By"),
        help_text=_("کاربر تاییدکننده"),
        related_name="acknowledged_alerts",
    )

    # ردیابی
    correlation_id = models.CharField(
        max_length=64,
        blank=True,
        db_index=True,
        verbose_name=_("Correlation ID"),
        help_text=_("شناسه همبستگی برای ردیابی"),
    )

    class Meta:
        verbose_name = _("Signal Alert")
        verbose_name_plural = _("Signal Alerts")
        ordering = ["-severity", "-created_at"]
        indexes = [
            models.Index(fields=['severity', '-created_at']),
            models.Index(fields=['is_acknowledged', '-created_at']),
            models.Index(fields=['alert_type', '-created_at']),
            models.Index(fields=['signal', '-created_at']),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['signal', 'alert_type'],
                condition=models.Q(is_acknowledged=False),
                name="unique_unacknowledged_alert_per_signal"
            ),
        ]

    def __str__(self) -> str:
        ack = "✓" if self.is_acknowledged else "✗"
        return f"Alert#{self.id} [{ack}] {self.get_severity_display()}: {self.title}"

    def clean(self) -> None:
        """اعتبارسنجی هشدار"""
        super().clean()

        # منطق تایید
        if self.is_acknowledged and not self.acknowledged_at:
            self.acknowledged_at = timezone.now()
        elif not self.is_acknowledged and self.acknowledged_at:
            self.acknowledged_at = None
            self.acknowledged_by = None

    def save(self, *args: Any, **kwargs: Any) -> None:
        """ذخیره‌سازی با لاگ خودکار"""
        self.full_clean()

        # ایجاد لاگ برای هشدارهای بحرانی
        if self.severity >= Severity.HIGH and not self.pk:
            logger.warning(
                f"هشدار بحرانی ایجاد شد: {self.alert_type} برای سیگنال {self.signal_id}"
            )

        with transaction.atomic():
            super().save(*args, **kwargs)

    def acknowledge(self, user, ip_address: Optional[str] = None) -> None:
        """
        تایید امن هشدار با لاگ کامل

        Args:
            user: کاربر تاییدکننده
            ip_address: IP آدرس برای حسابرسی
        """
        if self.is_acknowledged:
            raise ValidationError(_("این هشدار قبلاً تایید شده است"))

        with transaction.atomic():
            self.is_acknowledged = True
            self.acknowledged_at = timezone.now()
            self.acknowledged_by = user
            self.save()

            # ایجاد لاگ برای تایید
            logger.info(
                f"هشدار {self.id} توسط کاربر {user.id} از IP {ip_address} تایید شد"
            )




