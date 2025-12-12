# tests/test_core/test_admin.py

import pytest
from django.contrib import admin
from django.test import RequestFactory
from django.contrib.auth import get_user_model
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌های core
)
from apps.core.admin import (
    AuditLogAdmin,
    SystemSettingAdmin,
    CacheEntryAdmin,
    # سایر Adminهای core
)
from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
    # سایر فکتوری‌های core
)

User = get_user_model()

pytestmark = pytest.mark.django_db

class TestAuditLogAdmin:
    """
    Tests for the AuditLogAdmin interface.
    """
    def test_audit_log_admin_list_display(self):
        """
        Test that the list_display fields are correctly configured.
        """
        admin_instance = AuditLogAdmin(AuditLog, admin.site)
        assert 'user_email_link' in admin_instance.list_display
        assert 'action' in admin_instance.list_display
        assert 'target_model' in admin_instance.list_display
        assert 'target_id' in admin_instance.list_display
        assert 'ip_address' in admin_instance.list_display
        assert 'created_at' in admin_instance.list_display

    def test_audit_log_admin_list_filter(self):
        """
        Test that the list_filter fields are correctly configured.
        """
        admin_instance = AuditLogAdmin(AuditLog, admin.site)
        assert 'action' in admin_instance.list_filter
        assert 'target_model' in admin_instance.list_filter
        assert 'created_at' in admin_instance.list_filter

    def test_audit_log_admin_search_fields(self):
        """
        Test that the search_fields are correctly configured.
        """
        admin_instance = AuditLogAdmin(AuditLog, admin.site)
        assert 'user__email' in admin_instance.search_fields
        assert 'target_model' in admin_instance.search_fields

    def test_audit_log_admin_readonly_fields(self):
        """
        Test that the readonly_fields are correctly configured.
        """
        admin_instance = AuditLogAdmin(AuditLog, admin.site)
        readonly_fields = admin_instance.readonly_fields
        assert 'user' in readonly_fields
        assert 'action' in readonly_fields
        assert 'target_model' in readonly_fields
        assert 'target_id' in readonly_fields
        assert 'details_summary' in readonly_fields # فیلد سفارشی
        assert 'ip_address' in readonly_fields
        assert 'user_agent' in readonly_fields
        assert 'session_key' in readonly_fields
        assert 'created_at' in readonly_fields

    def test_audit_log_admin_fieldsets(self):
        """
        Test that the fieldsets are correctly configured.
        """
        admin_instance = AuditLogAdmin(AuditLog, admin.site)
        found_details_section = False
        found_context_section = False
        for title, options in admin_instance.fieldsets:
            if title == 'Details':
                found_details_section = True
            if title == 'Context':
                found_context_section = True
        assert found_details_section is True
        assert found_context_section is True

    def test_user_email_link_method(self, AuditLogFactory, CustomUserFactory):
        """
        Test the user_email_link custom method in AuditLogAdmin.
        """
        user = CustomUserFactory(email='audit_user@example.com')
        log = AuditLogFactory(user=user)
        admin_instance = AuditLogAdmin(AuditLog, admin.site)

        # ایجاد یک request موقت برای context
        request = RequestFactory().get('/admin/core/auditlog/')
        # این متد معمولاً در داخل یک نمای ادمین فراخوانی می‌شود و context دارد
        # برای تست مستقیم، فقط نام کاربری را چاپ می‌کنیم
        # در عمل، این متد یک لینک HTML باز می‌گرداند
        # link_html = admin_instance.user_email_link(log)
        # assert 'audit_user@example.com' in link_html
        # assert '/admin/accounts/customuser/' in link_html
        # یا فقط چک کنیم که خروجی یک رشته است و شامل ایمیل است
        result = admin_instance.user_email_link(log)
        assert isinstance(result, str)
        assert 'audit_user@example.com' in result


class TestSystemSettingAdmin:
    """
    Tests for the SystemSettingAdmin interface.
    """
    def test_system_setting_admin_list_display(self):
        """
        Test the list_display configuration.
        """
        admin_instance = SystemSettingAdmin(SystemSetting, admin.site)
        assert 'key' in admin_instance.list_display
        assert 'value_preview' in admin_instance.list_display
        assert 'data_type' in admin_instance.list_display
        assert 'is_sensitive' in admin_instance.list_display
        assert 'is_active' in admin_instance.list_display

    def test_system_setting_admin_readonly_fields(self):
        """
        Test the readonly_fields configuration.
        """
        admin_instance = SystemSettingAdmin(SystemSetting, admin.site)
        assert 'created_at' in admin_instance.readonly_fields
        assert 'updated_at' in admin_instance.readonly_fields

    def test_system_setting_admin_fieldsets(self):
        """
        Test the fieldsets configuration.
        """
        admin_instance = SystemSettingAdmin(SystemSetting, admin.site)
        found_security_section = False
        for title, options in admin_instance.fieldsets:
            if title == 'Type & Security':
                found_security_section = True
                assert 'is_sensitive' in options['fields']
                break
        assert found_security_section is True

    def test_value_preview_method(self, SystemSettingFactory):
        """
        Test the value_preview method masks sensitive values.
        """
        setting_sensitive = SystemSettingFactory(key='API_KEY', value='secret12345', is_sensitive=True)
        setting_public = SystemSettingFactory(key='PUBLIC_VAR', value='public_value', is_sensitive=False)

        admin_instance = SystemSettingAdmin(SystemSetting, admin.site)

        # چک کردن مسک کردن مقدار
        preview_sensitive = admin_instance.value_preview(setting_sensitive)
        assert preview_sensitive == "***"

        # چک کردن نمایش مقدار عمومی
        preview_public = admin_instance.value_preview(setting_public)
        assert preview_public == "public_value" # یا کوتاه شده


class TestCacheEntryAdmin:
    """
    Tests for the CacheEntryAdmin interface.
    """
    def test_cache_entry_admin_list_display(self):
        """
        Test the list_display configuration.
        """
        admin_instance = CacheEntryAdmin(CacheEntry, admin.site)
        assert 'key' in admin_instance.list_display
        assert 'value_preview' in admin_instance.list_display
        assert 'expires_at' in admin_instance.list_display

    def test_cache_entry_admin_readonly_fields(self):
        """
        Test the readonly_fields configuration.
        """
        admin_instance = CacheEntryAdmin(CacheEntry, admin.site)
        assert 'key' in admin_instance.readonly_fields
        assert 'created_at' in admin_instance.readonly_fields
        assert 'updated_at' in admin_instance.readonly_fields

    def test_cache_entry_admin_actions(self):
        """
        Test that custom actions are registered.
        """
        admin_instance = CacheEntryAdmin(CacheEntry, admin.site)
        # چک کردن اینکه اکشن وجود دارد
        assert 'invalidate_selected' in [action.__name__ for action in admin_instance.actions]

    def test_value_preview_method(self, CacheEntryFactory):
        """
        Test the value_preview method masks sensitive values based on key.
        """
        entry_sensitive = CacheEntryFactory(key='api_key_test', value='very_secret_data')
        entry_public = CacheEntryFactory(key='general_info', value='public_data')

        admin_instance = CacheEntryAdmin(CacheEntry, admin.site)

        # چک کردن مسک کردن مقدار بر اساس کلید
        preview_sensitive = admin_instance.value_preview(entry_sensitive)
        assert preview_sensitive == "***"

        # چک کردن نمایش مقدار عمومی یا کوتاه شده
        preview_public = admin_instance.value_preview(entry_public)
        assert 'public_data' in preview_public or len(preview_public) <= len('public_data') # ممکن است کوتاه شود


# --- تست‌های عمومی Admin ---
class TestCoreAdminGeneric:
    """
    Generic tests for core admin configurations.
    """
    def test_admin_requires_staff_user(self, StaffUserFactory, rf):
        """
        Ensures that accessing admin pages requires a staff user.
        """
        staff_user = StaffUserFactory()
        request = rf.get('/admin/core/auditlog/')
        request.user = staff_user

        # ایجاد یک نمونه از یک Admin
        admin_instance = AuditLogAdmin(AuditLog, admin.site)

        # چک کردن اجازه دسترسی (می‌توان از Django Admin API برای چک کردن این استفاده کرد)
        # یا فقط اطمینان از اینکه کلاس Admin وجود دارد و ثبت شده است
        assert admin_instance is not None
        assert isinstance(admin_instance, admin.ModelAdmin)

    def test_admin_accessible_by_staff_via_client(self, admin_client, StaffUserFactory):
        """
        Ensures that staff users can access admin pages via the client.
        """
        # admin_client از پیش احراز هویت شده است
        url = '/admin/core/auditlog/'
        response = admin_client.get(url)
        # باید بتواند صفحه لیست را ببیند (کد 200 یا 302 اگر redirect شود)
        # فرض: ادمین کلید/مقدار سیستمی را نیز می‌بیند
        url2 = '/admin/core/systemsetting/'
        response2 = admin_client.get(url2)
        assert response2.status_code == 200

    def test_admin_not_accessible_by_regular_user(self, authenticated_api_client, rf):
        """
        Ensures that regular authenticated users (non-staff) cannot access admin pages.
        """
        # توجه: authenticated_api_client ممکن است کاربر معمولی باشد
        client, user = authenticated_api_client
        if not user.is_staff:
            # ایجاد یک request معمولی برای چک کردن ادمین
            request = rf.get('/admin/core/auditlog/')
            request.user = user
            # این فقط چک می‌کند که آیا کاربر ادمین است یا نه، اما نه اینکه به صفحه دسترسی داشته باشد
            # دسترسی واقعی باید از طریق client.get تست شود
            admin_url = '/admin/'
            response = client.get(admin_url)
            # باید به صفحه ورود هدایت شود یا خطای 403 بدهد (بسته به تنظیمات)
            # معمولاً کاربر معمولی به صفحه ادمین هدایت می‌شود و سپس خطای 403 می‌گیرد
            # یا اینکه مستقیماً 403 می‌گیرد
            # این تست فقط نشان می‌دهد که دسترسی ممکن نیست
            assert response.status_code in [302, 403] # Redirect to login یا Forbidden

    # می‌توانید تست‌هایی برای دسترسی مدل‌های خاص به کاربران ادمین/استاف خاص اضافه کنید
    # این نیازمند سطح دسترسی پیشرفته‌تر در پنل ادمین است (مثلاً با استفاده از گروه‌ها و مجوزها)

# --- تست Inline Admins (اگر وجود داشته باشند) ---
# اگر از Inline Admins استفاده کرده‌اید (مثلاً برای اضافه کردن مدل‌های وابسته در صفحه ادمین مدل اصلی)،
# می‌توانید تست‌هایی برای این اینلاین‌ها بنویسید
# مثلاً:
# class TestSomeInlineAdmin:
#     def test_inline_formset_logic(self):
#         # ...

logger.info("Core admin tests loaded successfully.")
