# apps/accounts/admin.py

from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import CustomUser, UserProfile, UserSession, UserAPIKey


@admin.register(CustomUser)
class CustomUserAdmin(BaseUserAdmin):
    """
    Admin interface for the CustomUser model.
    """
    # تعیین فیلدهایی که در فرم ویرایش نمایش داده می‌شوند
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('username_display', 'first_name', 'last_name')}),
        (_('User Type'), {'fields': ('user_type',)}),
        (_('Status'), {'fields': ('is_active', 'is_verified', 'is_locked', 'is_demo')}),
        (_('Security'), {
            'fields': ('failed_login_attempts', 'locked_until', 'last_login_ip', 'last_login_at'),
            'classes': ('collapse',)  # جهت کاهش فضای اشغالی بخش امنیتی
        }),
        (_('Permissions'), {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        (_('Important dates'), {'fields': ('last_login', 'date_joined', 'password_changed_at')}), # افزودن فیلد جدید
    )
    # تعیین فیلدهایی که در هنگام ایجاد کاربر جدید نمایش داده می‌شوند
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'username_display', 'user_type', 'is_active'),
        }),
    )
    # ستون‌هایی که در لیست کاربران نمایش داده می‌شوند
    list_display = ('email', 'username_display', 'user_type', 'is_active', 'is_verified', 'is_demo', 'is_locked', 'last_login_at')
    # فیلترهایی که در سمت راست لیست کاربران نمایش داده می‌شوند
    list_filter = ('is_active', 'is_verified', 'is_demo', 'user_type', 'is_locked', 'failed_login_attempts')
    # فیلدهایی که قابل جستجو هستند
    search_fields = ('email', 'username_display')
    # فیلدی که لیست بر اساس آن مرتب می‌شود
    ordering = ('email',)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """
    Admin interface for the UserProfile model.
    """
    # تعیین فیلدهایی که در فرم ویرایش نمایش داده می‌شوند
    fieldsets = (
        (_('Personal Information'), {
            'fields': ('user', 'first_name', 'last_name', 'display_name', 'phone_number', 'nationality', 'date_of_birth', 'address')
        }),
        (_('Security Settings'), {
            'fields': ('two_factor_enabled', 'backup_codes', 'api_access_enabled', 'max_api_requests_per_minute', 'allowed_ips') # افزودن backup_codes
        }),
        (_('Trading Preferences'), {
            'fields': ('preferred_base_currency', 'default_leverage', 'risk_level', 'max_active_trades', 'max_capital')
        }),
        (_('Notification Preferences'), {
            'fields': ('notify_on_trade', 'notify_on_balance_change', 'notify_on_risk_limit_breach', 'notification_channels')
        }),
        (_('KYC/AML Information'), {
            'fields': ('is_kyc_verified', 'kyc_document_type', 'kyc_document_number', 'kyc_submitted_at', 'kyc_verified_at', 'kyc_rejected_at', 'kyc_rejection_reason')
        }),
    )
    # ستون‌هایی که در لیست پروفایل‌ها نمایش داده می‌شوند
    list_display = ('user', 'display_name', 'risk_level', 'is_kyc_verified', 'two_factor_enabled')
    # فیلترهایی که در سمت راست لیست پروفایل‌ها نمایش داده می‌شوند
    list_filter = ('risk_level', 'is_kyc_verified', 'two_factor_enabled', 'notify_on_trade')
    # فیلدهایی که قابل جستجو هستند
    search_fields = ('user__email', 'display_name', 'first_name', 'last_name')
    # فیلد user را به صورت لینک‌دار نمایش می‌دهد (برای جلوگیری از لود شدن کامل اطلاعات کاربر)
    raw_id_fields = ('user',)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """
    Admin interface for the UserSession model.
    """
    # ستون‌هایی که در لیست جلسات نمایش داده می‌شوند
    list_display = ('user', 'ip_address', 'device_fingerprint', 'is_active', 'expires_at')
    # فیلترهایی که در سمت راست لیست جلسات نمایش داده می‌شوند
    list_filter = ('is_active', 'expires_at')
    # فیلدهایی که قابل جستجو هستند
    search_fields = ('user__email', 'ip_address', 'device_fingerprint') # جستجو بر اساس اثر دستگاه نیز امکان‌پذیر است
    # فیلدهایی که فقط خواندنی هستند (عدم امکان ویرایش)
    readonly_fields = ('user', 'session_key', 'ip_address', 'user_agent', 'device_fingerprint', 'location', 'expires_at')


@admin.register(UserAPIKey)
class UserAPIKeyAdmin(admin.ModelAdmin):
    """
    Admin interface for the UserAPIKey model.
    """
    # ستون‌هایی که در لیست کلیدهای API نمایش داده می‌شوند
    list_display = ('user', 'name', 'is_active', 'expires_at', 'last_used_at', 'rate_limit_per_minute')
    # فیلترهایی که در سمت راست لیست کلیدهای API نمایش داده می‌شوند
    list_filter = ('is_active', 'expires_at', 'user') # فیلتر بر اساس کاربر نیز اضافه شد
    # فیلدهایی که قابل جستجو هستند
    search_fields = ('user__email', 'name', 'key') # جستجو بر اساس کلید نیز امکان‌پذیر است
    # فیلدهایی که فقط خواندنی هستند (عدم امکان ویرایش)
    readonly_fields = ('key', 'secret', 'last_used_at')
    # فیلدی که در فرم ویرایش نمایش داده می‌شود
    fieldsets = (
        (None, {'fields': ('user', 'name', 'is_active')}),
        (_('API Key Details'), {'fields': ('key', 'secret', 'expires_at', 'last_used_at', 'rate_limit_per_minute', 'permissions')}),
    )
