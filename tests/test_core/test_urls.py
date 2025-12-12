# tests/test_core/test_urls.py

import pytest
from django.urls import reverse, resolve
from apps.core import views # فرض بر این است که نماهای مربوط به core یا مدل‌های پایه در این فایل یا دیگر فایل‌های core قرار دارند
from apps.core.models import (
    AuditLog,
    SystemSetting,
    CacheEntry,
)
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد

pytestmark = pytest.mark.django_db

class TestCoreURLs:
    """
    Tests for the URL patterns defined in the core app's urls.py.
    Verifies that URLs resolve to the correct views and vice versa.
    """

    def test_audit_log_list_url_resolves(self):
        """
        Test that the audit log list URL resolves to the correct ViewSet action.
        """
        url = reverse('core:auditlog-list') # فرض: app_name='core' در urls.py اصلی تنظیم شده است
        assert resolve(url).func.cls == views.AuditLogViewSet # فرض: ViewSet استفاده شده است
        assert resolve(url).func.initkwargs['basename'] == 'auditlog'

    def test_audit_log_detail_url_resolves(self, AuditLogFactory):
        """
        Test that the audit log detail URL resolves correctly.
        """
        log = AuditLogFactory()
        url = reverse('core:auditlog-detail', kwargs={'pk': log.id})
        resolved_func = resolve(url).func
        # چک کردن کلاس ViewSet
        assert resolved_func.cls == views.AuditLogViewSet
        # چک کردن اینکه آیا action retrieve است یا نه (متدی که این URL را مدیریت می‌کند)
        # این کار با استفاده از resolver_match یا initkwargs انجام می‌شود
        # assert resolved_func.initkwargs['action'] == 'retrieve' # این کار نمی‌کند به این صورت
        # روش دیگر: اطمینان از اینکه pk در URL قرار گرفته و resolve می‌شود
        match = resolve(url)
        assert match.kwargs['pk'] == str(log.id) # IDها معمولاً به رشته تبدیل می‌شوند

    def test_system_setting_list_url_resolves(self):
        """
        Test that the system setting list URL resolves to the correct ViewSet action.
        """
        url = reverse('core:systemsetting-list')
        assert resolve(url).func.cls == views.SystemSettingViewSet
        assert resolve(url).func.initkwargs['basename'] == 'systemsetting'

    def test_system_setting_detail_url_resolves(self, SystemSettingFactory):
        """
        Test that the system setting detail URL resolves correctly.
        """
        setting = SystemSettingFactory()
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        match = resolve(url)
        assert match.cls == views.SystemSettingViewSet
        assert match.kwargs['pk'] == str(setting.id)

    def test_cache_entry_list_url_resolves(self):
        """
        Test that the cache entry list URL resolves to the correct ViewSet action.
        """
        url = reverse('core:cacheentry-list')
        assert resolve(url).func.cls == views.CacheEntryViewSet
        assert resolve(url).func.initkwargs['basename'] == 'cacheentry'

    def test_cache_entry_detail_url_resolves(self, CacheEntryFactory):
        """
        Test that the cache entry detail URL resolves correctly.
        """
        entry = CacheEntryFactory()
        url = reverse('core:cacheentry-detail', kwargs={'pk': entry.id})
        match = resolve(url)
        assert match.cls == views.CacheEntryViewSet
        assert match.kwargs['pk'] == str(entry.id)

    # --- تست سایر URLها ---
    # می‌توانید برای سایر endpointهایی که در urls.py تعریف کرده‌اید نیز تست بنویسید
    # مثلاً:
    # def test_custom_endpoint_resolves(self):
    #     url = reverse('core:custom-endpoint')
    #     assert resolve(url).func.view_class == views.CustomView
    #     # یا اگر از تابع استفاده کرده باشید:
    #     # assert resolve(url).func == views.custom_function_view

    # --- تست نام‌های URLها ---
    def test_audit_log_list_url_name(self):
        """
        Test the canonical name for the audit log list endpoint.
        """
        expected_url = '/core/audit-logs/' # فرض بر این است که این مسیر در urls.py قرار دارد
        actual_url = reverse('core:auditlog-list')
        assert actual_url == expected_url

    def test_system_setting_detail_url_name(self):
        """
        Test the canonical name for the system setting detail endpoint.
        """
        # این فقط یک چک ساده برای نام URL است
        # برای چک کردن مسیر کامل با ID، باید یک نمونه از مدل بسازید
        # مثال: چک کردن اینکه آیا نام URL وجود دارد یا خیر
        try:
            # این خط خطا می‌دهد چون نیاز به ID دارد
            # reverse('core:systemsetting-detail')
            # بنابراین فقط چک می‌کنیم که نام وجود دارد
            # resolve نیز می‌تواند نام را برگرداند
            resolved = resolve('/core/system-settings/12345678-1234-5678-9012-123456789012/') # یک مسیر نمونه
            assert resolved.url_name == 'systemsetting-detail'
        except: # Resolver404 یا ValueError
            # اگر مسیر وجود نداشت یا نام نادرست بود، این تست ناموفق است
            # برای این تست، باید مطمئن شوید که مسیر `/core/system-settings/<uuid:pk>/` تعریف شده است
            # و app_name نیز core است
            pytest.fail("System setting detail URL did not resolve correctly.")


    # --- تست اتصال به نماهای ادمین ---
    # این معمولاً در تست‌های ادمین (admin.py) انجام می‌شود، نه در urls.py
    # اما می‌توانید چک کنید که آیا مسیرهای ادمین درست ثبت شده‌اند یا خیر
    # def test_admin_audit_log_changelist_url(self):
    #     url = reverse('admin:core_auditlog_changelist')
    #     # می‌توانید چک کنید که آیا resolve می‌شود یا خیر
    #     resolved = resolve(url)
    #     # این نشان می‌دهد که مسیر ادمین وجود دارد
    #     assert resolved.app_name == 'admin'
    #     assert resolved.url_name == 'core_auditlog_changelist'

# --- تست URLهای عمومی ---
class TestCorePublicURLs:
    """
    Tests for public/core URLs that might not be part of a specific ViewSet.
    """
    def test_health_check_url_resolves(self):
        """
        Test resolving the health check URL.
        """
        url = reverse('core:health-check') # فرض: در urls.py اصلی یا core/urls.py تعریف شده است
        assert resolve(url).func.view_class == views.HealthCheckView

    def test_ping_url_resolves(self):
        """
        Test resolving the ping URL.
        """
        url = reverse('core:ping') # فرض: در urls.py اصلی یا core/urls.py تعریف شده است
        assert resolve(url).func.view_class == views.PingView

# --- تست سایر موارد ---
# می‌توانید تست‌هایی برای 404 یا redirects یا سایر رفتارهای URL نیز بنویسید
# مثلاً:
# def test_nonexistent_url(self, api_client):
#     response = api_client.get('/core/nonexistent-endpoint/')
#     assert response.status_code == 404

logger.info("Core URL tests loaded successfully.")
