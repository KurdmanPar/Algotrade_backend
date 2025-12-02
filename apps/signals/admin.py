# apps/signals/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import PermissionDenied
from django.utils.html import format_html
from django.contrib import messages
from django.db.models import QuerySet
from django.utils import timezone
from django.db import transaction
from typing import Any, Optional
import logging

from .models import Signal, SignalLog, SignalAlert, SignalStatus, AlertType, Severity

logger = logging.getLogger(__name__)


# -------------------- Mixins امنیتی --------------------

class ReadOnlyAdminMixin:
    """
    Mixin برای جلوگیری از ویرایش یا حذف در ادمین
    برای مدل‌هایی که باید فقط‌خواندنی باشند (مثل لاگ‌ها)
    """

    def has_add_permission(self, request, obj=None) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


class AuditLogAdminMixin:
    """
    Mixin برای لاگ کردن تمام عملیات ادمین
    """

    def log_addition(self, request, object, message):
        logger.info(f"ADMIN ADD: User {request.user.id} added {object.__class__.__name__}#{object.id}")
        super().log_addition(request, object, message)

    def log_change(self, request, object, message):
        logger.info(
            f"ADMIN CHANGE: User {request.user.id} changed {object.__class__.__name__}#{object.id}: {message}"
        )
        super().log_change(request, object, message)

    def log_deletion(self, request, object, object_repr):
        logger.warning(
            f"ADMIN DELETE: User {request.user.id} deleted {object_repr} (ID: {object.id})"
        )
        super().log_deletion(request, object, object_repr)


# -------------------- Signal Admin --------------------

@admin.register(Signal)
class SignalAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    """
    ادمین امن برای مدیریت سیگنال‌ها با کنترل دسترسی دقیق
    """

    # نمایش لیست
    list_display = (
        'id',
        'user',
        'bot',
        'instrument',
        'direction_colored',
        'signal_type',
        'status_colored',
        'confidence_score',
        'quantity',
        'price',
        'generated_at',
        'is_expired_indicator',
    )
    list_filter = (
        'status',
        'direction',
        'signal_type',
        'generated_at',
        'is_recurring',
        'sent_to_risk',
        'sent_to_execution',
    )
    search_fields = (
        'id',
        'correlation_id',
        'instrument__symbol',
        'user__username',
        'user__email',
    )
    ordering = ('-generated_at',)
    date_hierarchy = 'generated_at'

    # فیلدهای ارتباطی با کارایی بالا
    autocomplete_fields = (
        'user',
        'bot',
        'strategy_version',
        'agent',
        'exchange_account',
        'instrument',
        'final_order',
    )

    # فیلدهای افقی برای خوانایی
    list_select_related = (
        'user',
        'bot',
        'strategy_version',
        'agent',
        'exchange_account',
        'instrument',
        'final_order',
    )

    # فیلدهای فقط‌خواندنی پس از ایجاد
    readonly_fields = (
        'id',
        'correlation_id',
        'created_at',
        'updated_at',
        'created_by_ip',
        'user_agent',
        'sent_to_risk',
        'sent_to_execution',
        'executed_at',
        'is_expired_indicator',
    )

    # فیلدهای قابل ویرایش در فرم
    fieldsets = (
        (_('اطلاعات پایه'), {
            'fields': ('user', 'bot', 'strategy_version', 'agent', 'exchange_account', 'instrument')
        }),
        (_('اطلاعات معامله'), {
            'fields': ('direction', 'signal_type', 'quantity', 'price')
        }),
        (_('پارامترهای سیگنال'), {
            'fields': ('confidence_score', 'payload', 'status', 'priority', 'is_recurring')
        }),
        (_('زمان‌بندی'), {
            'fields': ('generated_at', 'expires_at', 'processed_at', 'executed_at')
        }),
        (_('اطلاعات ردیابی و امنیت'), {
            'fields': ('correlation_id', 'risk_approval_details', 'created_by_ip', 'user_agent'),
            'classes': ('collapse',)
        }),
    )

    actions = ['cancel_signals', 'approve_signals', 'export_signals_csv']

    # ----- متدهای امنیتی -----

    def get_queryset(self, request) -> QuerySet:
        """فیلتر خودکار بر اساس دسترسی کاربر"""
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            # کاربران عادی فقط سیگنال‌های خودشان را ببینند
            qs = qs.filter(user=request.user)
        return qs.select_related(
            'user', 'bot', 'strategy_version', 'agent', 'exchange_account', 'instrument'
        )

    def has_change_permission(self, request, obj: Optional[Signal] = None) -> bool:
        """
        کنترل دسترسی ویرایش: فقط کاربران مجاز می‌توانند سیگنال‌ها را ویرایش کنند
        """
        if obj and not request.user.is_superuser:
            # فقط کاربر ایجادکننده یا مدیران می‌توانند ویرایش کنند
            if obj.user != request.user:
                return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj: Optional[Signal] = None) -> bool:
        """جلوگیری از حذف سیگنال‌ها - برای حفظ یکپارچگی داده"""
        return False

    # ----- متدهای نمایشی -----

    def direction_colored(self, obj: Signal) -> str:
        """نمایش رنگی جهت معامله"""
        colors = {
            'BUY': 'green',
            'SELL': 'red',
            'CLOSE_LONG': 'orange',
            'CLOSE_SHORT': 'purple',
        }
        color = colors.get(obj.direction, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_direction_display()
        )

    direction_colored.short_description = _("Direction")
    direction_colored.admin_order_field = 'direction'

    def status_colored(self, obj: Signal) -> str:
        """نمایش رنگی وضعیت"""
        colors = {
            'PENDING': 'gray',
            'APPROVED': 'green',
            'REJECTED': 'red',
            'EXECUTED': 'blue',
            'EXPIRED': 'orange',
            'CANCELED': 'darkred',
            'SENT_TO_RISK': 'cyan',
            'SENT_TO_EXECUTION': 'purple',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display()
        )

    status_colored.short_description = _("Status")
    status_colored.admin_order_field = 'status'

    def is_expired_indicator(self, obj: Signal) -> str:
        """نمایش وضعیت انقضا"""
        if obj.is_expired():
            return format_html('<span style="color: red;">✓</span>')
        return format_html('<span style="color: green;">✗</span>')

    is_expired_indicator.short_description = _("Expired")
    is_expired_indicator.boolean = True

    # ----- اکشن‌های ادمین -----

    @admin.action(description=_("لغو سیگنال‌های انتخاب‌شده"))
    def cancel_signals(self, request, queryset: QuerySet):
        """لغو ایمن سیگنال‌های انتخاب‌شده"""
        if not request.user.has_perm('signals.can_cancel_signal'):
            raise PermissionDenied(_("شما دسترسی لغو سیگنال را ندارید"))

        updated = 0
        for signal in queryset.select_for_update():
            if signal.status in ['PENDING', 'SENT_TO_RISK']:
                try:
                    with transaction.atomic():
                        signal.status = SignalStatus.CANCELED
                        signal.save()
                        updated += 1
                except Exception as e:
                    self.message_user(request, str(e), level=messages.ERROR)

        self.message_user(request, f"{updated} سیگنال با موفقیت لغو شد.", level=messages.SUCCESS)

    @admin.action(description=_("تایید سیگنال‌های انتخاب‌شده"))
    def approve_signals(self, request, queryset: QuerySet):
        """تایید دستی سیگنال‌ها (فقط برای مدیران)"""
        if not request.user.is_staff:
            raise PermissionDenied(_("فقط کارکنان مجاز به تایید دستی هستند"))

        updated = 0
        for signal in queryset.select_for_update():
            if signal.status == SignalStatus.PENDING:
                try:
                    with transaction.atomic():
                        signal.status = SignalStatus.APPROVED
                        signal.risk_approval_details = {
                            "manual_approval": True,
                            "approved_by": request.user.id,
                            "approved_at": timezone.now().isoformat(),
                            "ip": self._get_client_ip(request),
                        }
                        signal.save()
                        updated += 1
                except Exception as e:
                    self.message_user(request, str(e), level=messages.ERROR)

        self.message_user(request, f"{updated} سیگنال تایید شد.", level=messages.SUCCESS)

    @admin.action(description=_("خروجی CSV از سیگنال‌ها"))
    def export_signals_csv(self, request, queryset: QuerySet):
        """خروجی گرفتن CSV (با فیلتر دسترسی)"""
        import csv
        from django.http import HttpResponse

        if not request.user.has_perm('signals.can_export'):
            raise PermissionDenied(_("دسترسی خروجی‌گیری ندارید"))

        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="signals.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'ID', 'User', 'Symbol', 'Direction', 'Type', 'Status',
            'Quantity', 'Price', 'Confidence', 'Generated At'
        ])

        for signal in queryset:
            writer.writerow([
                signal.id,
                signal.user.username,
                signal.instrument.symbol,
                signal.direction,
                signal.signal_type,
                signal.status,
                signal.quantity,
                signal.price or '',
                signal.confidence_score,
                signal.generated_at,
            ])

        return response

    # ----- متدهای کمکی -----

    def _get_client_ip(self, request) -> Optional[str]:
        """دریافت IP امن کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    def save_model(self, request, obj: Signal, form, change):
        """ذخیره‌سازی با لاگ کامل و احراز هویت"""
        obj._changed_by_user = request.user

        # ذخیره IP و User Agent برای ردیابی
        if not change:  # در هنگام ایجاد
            obj.created_by_ip = self._get_client_ip(request)
            obj.user_agent = request.META.get('HTTP_USER_AGENT', '')[:512]

        super().save_model(request, obj, form, change)


# -------------------- SignalLog Admin --------------------

@admin.register(SignalLog)
class SignalLogAdmin(ReadOnlyAdminMixin, AuditLogAdminMixin, admin.ModelAdmin):
    """
    ادمین فقط‌خواندنی برای لاگ‌های سیگنال
    """

    list_display = (
        'id',
        'signal_link',
        'old_status',
        'new_status',
        'created_at',
        'changed_by',
    )
    list_filter = (
        'new_status',
        'changed_by_agent',
        'changed_by_user',
        'created_at',
    )
    search_fields = (
        'signal__id',
        'signal__correlation_id',
        'message',
    )
    ordering = ('-created_at',)
    date_hierarchy = 'created_at'

    # فقط‌خواندنی
    readonly_fields = (
        'signal',
        'old_status',
        'new_status',
        'message',
        'details',
        'changed_by_agent',
        'changed_by_user',
        'ip_address',
        'user_agent',
        'created_at',
    )

    # ارتباطات کارا
    autocomplete_fields = ('signal', 'changed_by_agent', 'changed_by_user')
    list_select_related = ('signal', 'changed_by_agent', 'changed_by_user')

    def signal_link(self, obj: SignalLog) -> str:
        """لینک به سیگنال مادر"""
        from django.urls import reverse
        url = reverse('admin:signals_signal_change', args=[obj.signal_id])
        return format_html('<a href="{}">Signal#{}</a>', url, obj.signal_id)

    signal_link.short_description = _("Signal")

    def changed_by(self, obj: SignalLog) -> str:
        """نمایش ویرایش‌کننده"""
        if obj.changed_by_agent:
            return f"Agent: {obj.changed_by_agent.name}"
        elif obj.changed_by_user:
            return f"User: {obj.changed_by_user.get_full_name()}"
        return _("System")

    changed_by.short_description = _("Changed By")

    def get_actions(self, request):
        """حذف تمام اکشن‌ها برای لاگ‌ها"""
        actions = super().get_actions(request)
        if actions:
            actions.clear()
        return actions


# -------------------- SignalAlert Admin --------------------

@admin.register(SignalAlert)
class SignalAlertAdmin(AuditLogAdminMixin, admin.ModelAdmin):
    """
    ادمین برای مدیریت هشدارها با تایید امن
    """

    list_display = (
        'id',
        'signal_link',
        'alert_type_colored',
        'severity_colored',
        'title',
        'is_acknowledged',
        'created_at',
    )
    list_filter = (
        'alert_type',
        'severity',
        'is_acknowledged',
        'created_at',
    )
    search_fields = (
        'signal__id',
        'title',
        'description',
        'correlation_id',
    )
    ordering = ('-severity', '-created_at')
    date_hierarchy = 'created_at'

    # ارتباطات کارا
    autocomplete_fields = ('signal', 'acknowledged_by')
    list_select_related = ('signal', 'acknowledged_by')

    # فیلدهای فقط‌خواندنی
    readonly_fields = (
        'id',
        'correlation_id',
        'created_at',
        'updated_at',
        'acknowledged_at',
    )

    # فیلدهای افقی
    fields = (
        ('signal', 'correlation_id'),
        ('alert_type', 'severity'),
        'title',
        'description',
        'details',
        ('is_acknowledged', 'acknowledged_by', 'acknowledged_at'),
        ('created_at', 'updated_at'),
    )

    actions = ['acknowledge_alerts']

    def signal_link(self, obj: SignalAlert) -> str:
        """لینک به سیگنال مادر"""
        from django.urls import reverse
        url = reverse('admin:signals_signal_change', args=[obj.signal_id])
        return format_html('<a href="{}">Signal#{}</a>', url, obj.signal_id)

    signal_link.short_description = _("Signal")

    def alert_type_colored(self, obj: SignalAlert) -> str:
        """نمایش رنگی نوع هشدار"""
        colors = {
            'HIGH_CONFIDENCE': 'green',
            'RISK_REJECTION': 'red',
            'EXECUTION_ERROR': 'darkred',
            'MANUAL_OVERRIDE': 'orange',
        }
        color = colors.get(obj.alert_type, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_alert_type_display()
        )

    alert_type_colored.short_description = _("Alert Type")

    def severity_colored(self, obj: SignalAlert) -> str:
        """نمایش رنگی شدت"""
        colors = {
            1: 'green',  # LOW
            2: 'orange',  # MEDIUM
            3: 'red',  # HIGH
            4: 'darkred',  # CRITICAL
        }
        color = colors.get(obj.severity, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_severity_display()
        )

    severity_colored.short_description = _("Severity")

    @admin.action(description=_("تایید هشدارهای انتخاب‌شده"))
    def acknowledge_alerts(self, request, queryset: QuerySet):
        """تایید گروهی هشدارها با لاگ"""
        updated = 0
        for alert in queryset.filter(is_acknowledged=False):
            try:
                alert.acknowledge(request.user, self._get_client_ip(request))
                updated += 1
            except Exception as e:
                self.message_user(request, str(e), level=messages.ERROR)

        self.message_user(request, f"{updated} هشدار تایید شد.", level=messages.SUCCESS)

    def has_change_permission(self, request, obj: Optional[SignalAlert] = None) -> bool:
        """
        کنترل دسترسی: فقط کاربران مجاز می‌توانند هشدارها را تایید کنند
        """
        if obj and obj.is_acknowledged:
            # پس از تایید، غیرقابل ویرایش
            return False
        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj: Optional[SignalAlert] = None) -> bool:
        """جلوگیری از حذف هشدارهای بحرانی"""
        if obj and obj.severity >= Severity.HIGH:
            return False
        return super().has_delete_permission(request, obj)

    def save_model(self, request, obj: SignalAlert, form, change):
        """ذخیره‌سازی با احراز هویت"""
        if change and 'is_acknowledged' in form.changed_data:
            obj.acknowledged_by = request.user

        super().save_model(request, obj, form, change)

    def _get_client_ip(self, request) -> Optional[str]:
        """دریافت IP امن کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip