# apps/core/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌های احتمالی core
    # InstrumentGroup,
    # InstrumentCategory,
    # Instrument,
    # InstrumentExchangeMap,
    # IndicatorGroup,
    # Indicator,
    # IndicatorParameter,
    # IndicatorTemplate,
    # PriceActionPattern,
    # SmartMoneyConcept,
    # AIMetric,
    # InstrumentWatchlist,
)

# --- مدیریت مدل‌های Core ---

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    Admin interface for the AuditLog model.
    Provides detailed view and filtering for system events.
    """
    list_display = (
        'user_email_link', 'action', 'target_model', 'target_id', 'ip_address', 'created_at'
    )
    list_filter = ('action', 'target_model', 'created_at', 'user')
    search_fields = ('user__email', 'target_model', 'details', 'ip_address')
    readonly_fields = (
        'user', 'action', 'target_model', 'target_id', 'details_summary', 'ip_address', 'user_agent', 'session_key', 'created_at'
    )
    date_hierarchy = 'created_at'
    ordering = ['-created_at']

    def user_email_link(self, obj):
        """
        Creates a link to the user's admin page if user exists.
        """
        if obj.user:
            url = reverse("admin:accounts_customuser_change", args=[obj.user.id]) # فرض: اپلیکیشن accounts، مدل CustomUser
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return "Anonymous"
    user_email_link.short_description = 'User Email'
    user_email_link.admin_order_field = 'user__email' # امکان مرتب‌سازی

    # متد برای نمایش بهتر فیلد JSON details
    def details_summary(self, obj):
        """
        Shows a summary of the details JSON field for easier reading in admin.
        """
        details = obj.details
        if isinstance(details, dict):
            # نمایش چند کلید اول
            summary_parts = []
            for key, value in list(details.items())[:3]: # فقط 3 مورد اول
                summary_parts.append(f"{key}: {str(value)[:30]}{'...' if len(str(value)) > 30 else ''}") # محدود کردن طول مقدار
            return " | ".join(summary_parts) if summary_parts else "No details"
        return str(details)[:100] + "..." if len(str(details)) > 100 else str(details) # اگر رشته بود
    details_summary.short_description = 'Details Summary'

    fieldsets = (
        (None, {
            'fields': ('user', 'action', 'target_model', 'target_id')
        }),
        ('Details', {
            'fields': ('details_summary', 'details'), # ممکن است بخواهید details را در collapsible قرار دهید
            'classes': ('collapse',) # قابل جمع شدن
        }),
        ('Context', {
            'fields': ('ip_address', 'user_agent', 'session_key'),
        }),
        ('Meta', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )


@admin.register(SystemSetting)
class SystemSettingAdmin(admin.ModelAdmin):
    """
    Admin interface for the SystemSetting model.
    Allows administrators to manage system-wide configurations.
    """
    list_display = ('key', 'value_preview', 'data_type', 'is_sensitive', 'is_active', 'created_at', 'updated_at')
    list_filter = ('data_type', 'is_sensitive', 'is_active', 'created_at', 'updated_at')
    search_fields = ('key', 'description')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('key', 'value', 'description', 'is_active')
        }),
        ('Type & Security', {
            'fields': ('data_type', 'is_sensitive'),
            'classes': ('collapse',) # قابل جمع شدن
        }),
        ('Meta', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def value_preview(self, obj):
        """
        Shows a masked or truncated preview of the value, especially if sensitive.
        """
        if obj.is_sensitive:
            return "***" # یا تابع mask_sensitive_data از helpers
        # اگر مقدار طولانی بود، فقط چند کاراکتر نشان دهید
        value_str = str(obj.value)
        if len(value_str) > 50:
            return value_str[:47] + "..."
        return value_str
    value_preview.short_description = 'Value (Preview)'

    # ممکن است بخواهید یک فیلد ورودی اضافه کنید در fieldsets یا یک تابع save_model بنویسید که کش را فعال/غیرفعال کند.
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # مثال: فعال‌سازی تاسک برای بروزرسانی کش تنظیمات
        # from .tasks import invalidate_system_setting_cache_task
        # invalidate_system_setting_cache_task.delay(obj.key)


@admin.register(CacheEntry)
class CacheEntryAdmin(admin.ModelAdmin):
    """
    Admin interface for the CacheEntry model.
    Allows administrators to inspect and manage cached data.
    """
    list_display = ('key', 'value_preview', 'expires_at', 'created_at', 'updated_at')
    list_filter = ('expires_at', 'created_at')
    search_fields = ('key',)
    readonly_fields = ('key', 'created_at', 'updated_at')
    actions = ['invalidate_selected'] # افزودن اکشن سفارشی

    def value_preview(self, obj):
        """
        Shows a preview of the cached value. Masks if it seems sensitive.
        """
        value_str = str(obj.value)
        # چک ساده: اگر کلید شامل 'api' یا 'key' بود، مقدار را مسک کن
        if any(keyword in obj.key.lower() for keyword in ['api', 'key', 'secret', 'token']):
             return "***"
        # در غیر این صورت، اگر طولانی بود، کوتاه کن
        if len(value_str) > 100:
            return value_str[:97] + "..."
        return value_str
    value_preview.short_description = 'Value (Preview)'

    def invalidate_selected(self, request, queryset):
        """
        Action to invalidate (delete) selected cache entries.
        """
        deleted_count, _ = queryset.delete()
        self.message_user(request, f"Successfully invalidated {deleted_count} cache entries.")
    invalidate_selected.short_description = "Invalidate selected cache entries"

    # ممکن است نیاز به متد خاصی برای بروزرسانی داشته باشید که امنیت بیشتری داشته باشد
    # def save_model(self, request, obj, form, change):
    #     # منطقی برای بروزرسانی کش یا اعتبارسنجی امنیتی ممکن است اضافه شود
    #     super().save_model(request, obj, form, change)


# --- مدیریت مدل‌های BaseOwnedModel و TimeStampedModel ---
# نکته: مدل‌های BaseModel, BaseOwnedModel, TimeStampedModel انتزاعی (abstract) هستند
# و نمی‌توانند مستقیماً در ادمین ثبت شوند.
# اما مدل‌هایی که از آن‌ها ارث می‌برند (مثلاً Instrument, Strategy, AgentLog) می‌توانند ادمین داشته باشند.
# مثال فرضی برای یک مدل واقعی که از BaseOwnedModel ارث می‌برد (مثلاً InstrumentWatchlist از instruments)
# اگر InstrumentWatchlist در اپلیکیشن instruments بود، اینجا نباید ثبت شود.
# اما اگر مدلی مانند 'CoreOwnedItem' وجود داشت که در اپلیکیشن core تعریف شده بود:
# @admin.register(CoreOwnedItem)
# class CoreOwnedItemAdmin(admin.ModelAdmin):
#     list_display = ('name', 'owner_username', 'created_at', 'updated_at')
#     list_filter = ('created_at', 'owner')
#     search_fields = ('name', 'owner__username')
#     readonly_fields = ('owner', 'created_at', 'updated_at')
#     raw_id_fields = ('owner',) # برای انتخاب کارآمد
#
#     def owner_username(self, obj):
#         return obj.owner.username
#     owner_username.short_description = 'Owner'
#     owner_username.admin_order_field = 'owner__username'

# --- مدیریت سایر مدل‌های Core ---
# مثال: اگر مدل InstrumentGroup در این اپلیکیشن بود:
# @admin.register(InstrumentGroup)
# class InstrumentGroupAdmin(admin.ModelAdmin):
#     list_display = ('name', 'description', 'default_tick_size', 'default_lot_size')
#     search_fields = ('name', 'description')

# مثال: اگر مدل IndicatorGroup در این اپلیکیشن بود:
# @admin.register(IndicatorGroup)
# class IndicatorGroupAdmin(admin.ModelAdmin):
#     list_display = ('name', 'description')
#     search_fields = ('name', 'description')

# --- ادمین‌های سایر مدل‌ها ---
# می‌توانید برای سایر مدل‌هایی که در apps/core/models.py تعریف کرده‌اید نیز Admin ایجاد کنید.
# مثلاً اگر مدل LogEvent وجود داشت:
# @admin.register(LogEvent)
# class LogEventAdmin(admin.ModelAdmin):
#     list_display = ('level', 'message', 'timestamp', 'source_component')
#     list_filter = ('level', 'timestamp', 'source_component')
#     search_fields = ('message', 'details')
#     date_hierarchy = 'timestamp'

# --- نکات مهم ---
# - از `readonly_fields` برای فیلدهایی استفاده کنید که نباید توسط ادمین تغییر کنند (مثل created_at، updated_at، owner در بسیاری از موارد).
# - از `raw_id_fields` برای فیلدهای ForeignKey با تعداد زیادی از اشیاء استفاده کنید تا عملکرد جستجو بهبود یابد.
# - از `list_filter` و `search_fields` برای تسهیل یافتن داده‌ها استفاده کنید.
# - از `fieldsets` برای سازماندهی فیلدها در فرم ادمین استفاده کنید.
# - از `actions` برای عملیات‌های گروهی (مثل حذف یا فعال/غیرفعال کردن) استفاده کنید.
# - از `date_hierarchy` برای فیلتر زمانی در لیست استفاده کنید.
# - از `mark_safe` و `format_html` برای نمایش HTML در `list_display` یا `readonly_fields` استفاده کنید (اگر امن باشد).
# - مراقب فیلدهای `is_sensitive` باشید و در ادمین نیز آن‌ها را مسک کنید.

logger.info("Admin interfaces for 'core' app loaded successfully.")
