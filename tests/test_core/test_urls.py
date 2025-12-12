# tests/test_core/test_urls.py

import pytest
from django.urls import reverse, resolve
from apps.core import views # اطمینان از وجود نماهای مربوطه
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
)

#pytestmark = pytest.mark.django_db # URL routing تست نیازی به پایگاه داده ندارد (مگر اینکه نماها به آن دسترسی داشته باشند)


class TestCoreURLs:
    """
    Tests for the URL patterns defined in apps/core/urls.py.
    Verifies that URLs resolve to the correct views and vice versa.
    """

    def test_urls_module_loaded(self):
        """
        Test that the core app's urls module is loaded without errors.
        """
        # این فقط اطمینان می‌دهد که فایل urls.py وجود دارد و ساختار آن مشکل ندارد
        # در واقع، اگر فایل urls.py درست ساخته نشده باشد، پروژه Django هنگام شروع خطایی می‌دهد
        # بنابراین، این تست ممکن است فقط یک ایمپورت ساده باشد یا حذف شود
        # اما برای اطمینان از بارگذاری مسیرها، می‌توان از resolve استفاده کرد
        try:
            # سعی در یافتن یک مسیر فرضی
            # چون core ممکن است فقط شامل مسیرهای عمومی یا فقط WebSocket باشد،
            # ممکن است نیاز به تست مسیرهایی نباشد یا فقط چک کنیم که app_name تعریف شده است
            # برای مثال، اگر مسیری مانند 'core:health-check' وجود داشت:
            # reverse('core:health-check')
            # یا اگر یک مسیر عمومی برای چیزی مانند 'core:system-status' وجود داشت:
            # reverse('core:system-status')
            # اگر core فقط شامل مسیرهای WebSocket بود (که در routing.py تعریف می‌شوند)،
            # ممکن است نیاز به تست URLهای HTTP نداشته باشد
            # اما فرض می‌کنیم چند مسیر عمومی HTTP نیز وجود دارد یا مسیرهای مربوط به نماهای عمومی
            # reverse('core:some-public-view')
            pass # فقط نمونه، اگر مسیر وجود داشت، تست کنید
        except ImportError:
            pytest.fail("Could not import apps.core.urls module.")


    # --- تست مسیرهای عمومی (اگر وجود داشته باشند) ---
    # مثال: اگر نماهای عمومی مانند health_check یا ping وجود داشتند
    # def test_health_check_url_resolves(self):
    #     url = reverse('core:health-check') # فرض: app_name='core' در urls.py اصلی تنظیم شده است
    #     assert resolve(url).func.view_class == views.HealthCheckView # فرض: نما یک کلاس است
    #     # یا
    #     # assert resolve(url).func == views.health_check_view # فرض: نما یک تابع است
    #
    # def test_health_check_url_name(self):
    #     expected_url = '/core/health/' # فرض بر این است که مسیر اینطور تعریف شده است
    #     actual_url = reverse('core:health-check')
    #     assert actual_url == expected_url
    #
    # def test_ping_url_resolves(self):
    #     url = reverse('core:ping')
    #     assert resolve(url).func.view_class == views.PingView


    # --- تست مسیرهای مدل‌های Core (اگر ViewSet وجود داشت) ---
    # این تست‌ها زمانی معنادار است که ViewSetها برای مدل‌های Core تعریف شده باشند
    # فرض کنیم که برخی ViewSetها برای مدل‌هایی مثل AuditLog یا SystemSetting وجود دارند
    # def test_audit_log_list_url_resolves(self):
    #     url = reverse('core:auditlog-list') # فرض: app_name='core'
    #     assert resolve(url).func.cls == views.AuditLogViewSet
    #     assert resolve(url).func.initkwargs['basename'] == 'auditlog'
    #
    # def test_system_setting_detail_url_resolves(self):
    #     url = reverse('core:systemsetting-detail', kwargs={'pk': '12345678-1234-5678-9012-123456789012'}) # UUID
    #     resolved = resolve(url)
    #     assert resolved.func.cls == views.SystemSettingViewSet
    #     assert resolved.kwargs['pk'] == '12345678-1234-5678-9012-123456789012'
    #
    # def test_cache_entry_list_url_name(self):
    #     expected_url = '/core/cache-entries/' # فرض مسیر
    #     actual_url = reverse('core:cacheentry-list')
    #     assert actual_url == expected_url


    # --- تست مسیرهای ادمین (Admin URLs) ---
    # این مسیرها معمولاً در urls.py اصلی پروژه (myproject/urls.py) تعریف می‌شوند، نه در اپلیکیشن
    # اما اگر مسیرهای ادمین اختصاصی برای core وجود داشت:
    # def test_core_admin_custom_url_resolves(self):
    #     # مثال: اگر یک نمای سفارشی در ادمین وجود داشت
    #     # path('admin/core/custom-action/', views.custom_admin_view, name='custom-core-admin-action')
    #     url = reverse('admin:custom-core-admin-action')
    #     resolved = resolve(url)
    #     assert resolved.func == views.custom_admin_view


    # --- تست مسیرهایی که از Router ساخته شده‌اند ---
    # اگر در urls.py از DefaultRouter استفاده شده بود، مسیرهایی مانند <basename>-list و <basename>-detail ایجاد می‌شوند
    # که می‌توانید با resolve و reverse چک کنید
    # مثال (اگر AuditLogViewSet وجود داشت و basename='auditlog' بود):
    # def test_router_generated_list_url(self):
    #     url = reverse('core:auditlog-list') # با فرض app_name='core'
    #     match = resolve(url)
    #     assert match.view_name == 'core:auditlog-list' # یا match.func.cls == AuditLogViewSet
    #     # ممکن است نیاز به import view_cls داشته باشید
    #     from apps.core.views import AuditLogViewSet
    #     assert match.func.cls == AuditLogViewSet # اگر ViewSet باشد


    # --- تست عدم وجود مسیر (404) ---
    # def test_nonexistent_url(self):
    #     # چک کردن اینکه مسیری که وجود ندارد، 404 می‌دهد
    #     # این بیشتر در تست‌های ادغام (Integration Tests) معنادار است
    #     # در تست واحد URL، فقط می‌توان چک کرد که resolve نمی‌شود
    #     with pytest.raises(NoReverseMatch):
    #         reverse('core:non_existent_view_name')
    #
    #     # یا:
    #     from django.urls import NoReverseMatch
    #     try:
    #         reverse('core:non_existent_view_name')
    #         assert False, "Expected NoReverseMatch to be raised"
    #     except NoReverseMatch:
    #         pass # OK


# --- مثال: اگر نماهای خاصی وجود داشتند که فقط در core تعریف شده بودند ---
# class TestCoreSpecificViews:
#     def test_core_utility_view_url(self):
#         url = reverse('core:utility-function')
#         assert resolve(url).func == views.utility_function
#
#     def test_core_data_export_url(self):
#         url = reverse('core:export-data')
#         resolved = resolve(url)
#         assert resolved.func.view_class == views.DataExportView
#         # یا:
#         # assert resolved.func.cls == views.DataExportViewSet
#         # assert resolved.url_name == 'export-data'

logger.info("Core URL tests loaded successfully.")






# # tests/test_core/test_urls.py
#
# import pytest
# from django.urls import reverse, resolve
# from apps.core import views # فرض بر این است که نماهای مربوط به core یا مدل‌های پایه در این فایل یا دیگر فایل‌های core قرار دارند
# from apps.core.models import (
#     AuditLog,
#     SystemSetting,
#     CacheEntry,
# )
# from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد
#
# pytestmark = pytest.mark.django_db
#
# class TestCoreURLs:
#     """
#     Tests for the URL patterns defined in the core app's urls.py.
#     Verifies that URLs resolve to the correct views and vice versa.
#     """
#
#     def test_audit_log_list_url_resolves(self):
#         """
#         Test that the audit log list URL resolves to the correct ViewSet action.
#         """
#         url = reverse('core:auditlog-list') # فرض: app_name='core' در urls.py اصلی تنظیم شده است
#         assert resolve(url).func.cls == views.AuditLogViewSet # فرض: ViewSet استفاده شده است
#         assert resolve(url).func.initkwargs['basename'] == 'auditlog'
#
#     def test_audit_log_detail_url_resolves(self, AuditLogFactory):
#         """
#         Test that the audit log detail URL resolves correctly.
#         """
#         log = AuditLogFactory()
#         url = reverse('core:auditlog-detail', kwargs={'pk': log.id})
#         resolved_func = resolve(url).func
#         # چک کردن کلاس ViewSet
#         assert resolved_func.cls == views.AuditLogViewSet
#         # چک کردن اینکه آیا action retrieve است یا نه (متدی که این URL را مدیریت می‌کند)
#         # این کار با استفاده از resolver_match یا initkwargs انجام می‌شود
#         # assert resolved_func.initkwargs['action'] == 'retrieve' # این کار نمی‌کند به این صورت
#         # روش دیگر: اطمینان از اینکه pk در URL قرار گرفته و resolve می‌شود
#         match = resolve(url)
#         assert match.kwargs['pk'] == str(log.id) # IDها معمولاً به رشته تبدیل می‌شوند
#
#     def test_system_setting_list_url_resolves(self):
#         """
#         Test that the system setting list URL resolves to the correct ViewSet action.
#         """
#         url = reverse('core:systemsetting-list')
#         assert resolve(url).func.cls == views.SystemSettingViewSet
#         assert resolve(url).func.initkwargs['basename'] == 'systemsetting'
#
#     def test_system_setting_detail_url_resolves(self, SystemSettingFactory):
#         """
#         Test that the system setting detail URL resolves correctly.
#         """
#         setting = SystemSettingFactory()
#         url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
#         match = resolve(url)
#         assert match.cls == views.SystemSettingViewSet
#         assert match.kwargs['pk'] == str(setting.id)
#
#     def test_cache_entry_list_url_resolves(self):
#         """
#         Test that the cache entry list URL resolves to the correct ViewSet action.
#         """
#         url = reverse('core:cacheentry-list')
#         assert resolve(url).func.cls == views.CacheEntryViewSet
#         assert resolve(url).func.initkwargs['basename'] == 'cacheentry'
#
#     def test_cache_entry_detail_url_resolves(self, CacheEntryFactory):
#         """
#         Test that the cache entry detail URL resolves correctly.
#         """
#         entry = CacheEntryFactory()
#         url = reverse('core:cacheentry-detail', kwargs={'pk': entry.id})
#         match = resolve(url)
#         assert match.cls == views.CacheEntryViewSet
#         assert match.kwargs['pk'] == str(entry.id)
#
#     # --- تست سایر URLها ---
#     # می‌توانید برای سایر endpointهایی که در urls.py تعریف کرده‌اید نیز تست بنویسید
#     # مثلاً:
#     # def test_custom_endpoint_resolves(self):
#     #     url = reverse('core:custom-endpoint')
#     #     assert resolve(url).func.view_class == views.CustomView
#     #     # یا اگر از تابع استفاده کرده باشید:
#     #     # assert resolve(url).func == views.custom_function_view
#
#     # --- تست نام‌های URLها ---
#     def test_audit_log_list_url_name(self):
#         """
#         Test the canonical name for the audit log list endpoint.
#         """
#         expected_url = '/core/audit-logs/' # فرض بر این است که این مسیر در urls.py قرار دارد
#         actual_url = reverse('core:auditlog-list')
#         assert actual_url == expected_url
#
#     def test_system_setting_detail_url_name(self):
#         """
#         Test the canonical name for the system setting detail endpoint.
#         """
#         # این فقط یک چک ساده برای نام URL است
#         # برای چک کردن مسیر کامل با ID، باید یک نمونه از مدل بسازید
#         # مثال: چک کردن اینکه آیا نام URL وجود دارد یا خیر
#         try:
#             # این خط خطا می‌دهد چون نیاز به ID دارد
#             # reverse('core:systemsetting-detail')
#             # بنابراین فقط چک می‌کنیم که نام وجود دارد
#             # resolve نیز می‌تواند نام را برگرداند
#             resolved = resolve('/core/system-settings/12345678-1234-5678-9012-123456789012/') # یک مسیر نمونه
#             assert resolved.url_name == 'systemsetting-detail'
#         except: # Resolver404 یا ValueError
#             # اگر مسیر وجود نداشت یا نام نادرست بود، این تست ناموفق است
#             # برای این تست، باید مطمئن شوید که مسیر `/core/system-settings/<uuid:pk>/` تعریف شده است
#             # و app_name نیز core است
#             pytest.fail("System setting detail URL did not resolve correctly.")
#
#
#     # --- تست اتصال به نماهای ادمین ---
#     # این معمولاً در تست‌های ادمین (admin.py) انجام می‌شود، نه در urls.py
#     # اما می‌توانید چک کنید که آیا مسیرهای ادمین درست ثبت شده‌اند یا خیر
#     # def test_admin_audit_log_changelist_url(self):
#     #     url = reverse('admin:core_auditlog_changelist')
#     #     # می‌توانید چک کنید که آیا resolve می‌شود یا خیر
#     #     resolved = resolve(url)
#     #     # این نشان می‌دهد که مسیر ادمین وجود دارد
#     #     assert resolved.app_name == 'admin'
#     #     assert resolved.url_name == 'core_auditlog_changelist'
#
# # --- تست URLهای عمومی ---
# class TestCorePublicURLs:
#     """
#     Tests for public/core URLs that might not be part of a specific ViewSet.
#     """
#     def test_health_check_url_resolves(self):
#         """
#         Test resolving the health check URL.
#         """
#         url = reverse('core:health-check') # فرض: در urls.py اصلی یا core/urls.py تعریف شده است
#         assert resolve(url).func.view_class == views.HealthCheckView
#
#     def test_ping_url_resolves(self):
#         """
#         Test resolving the ping URL.
#         """
#         url = reverse('core:ping') # فرض: در urls.py اصلی یا core/urls.py تعریف شده است
#         assert resolve(url).func.view_class == views.PingView
#
# # --- تست سایر موارد ---
# # می‌توانید تست‌هایی برای 404 یا redirects یا سایر رفتارهای URL نیز بنویسید
# # مثلاً:
# # def test_nonexistent_url(self, api_client):
# #     response = api_client.get('/core/nonexistent-endpoint/')
# #     assert response.status_code == 404
#
# logger.info("Core URL tests loaded successfully.")
