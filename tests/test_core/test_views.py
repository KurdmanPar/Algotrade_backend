# tests/test_core/test_views.py

import pytest
from django.urls import reverse
from rest_framework import status
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
)
from apps.core.serializers import (
    CoreBaseSerializer,
    CoreOwnedModelSerializer,
    TimeStampedModelSerializer,
    AuditLogSerializer,
    SystemSettingSerializer,
    CacheEntrySerializer,
)
from apps.core.permissions import IsOwnerOrReadOnly
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد

pytestmark = pytest.mark.django_db

# --- نماهای عمومی (Health Check, Ping) ---

class TestHealthCheckView:
    """
    Tests for the HealthCheckView.
    """
    def test_health_check_get(self, api_client):
        """
        Test GET request to health check endpoint.
        """
        url = reverse('core:health-check') # فرض: app_name='core' در urls.py اصلی تنظیم شده است
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'status' in response.data
        assert response.data['status'] == 'ok'

class TestPingView:
    """
    Tests for the PingView.
    """
    def test_ping_get(self, api_client):
        """
        Test GET request to ping endpoint.
        """
        url = reverse('core:ping') # فرض: app_name='core' در urls.py اصلی تنظیم شده است
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert 'pong' in response.data
        assert 'client_ip' in response.data


# --- نماهای مدل‌های Core ---

class TestAuditLogViewSet:
    """
    Tests for the AuditLogViewSet.
    """
    def test_list_audit_logs_authenticated(self, authenticated_api_client, AuditLogFactory):
        """
        Test listing audit logs for an authenticated user.
        """
        client, user = authenticated_api_client
        # ایجاد چند ورودی لاگ توسط کاربر فعلی
        AuditLogFactory.create_batch(3, user=user)
        # ایجاد یک ورودی توسط کاربر دیگر
        AuditLogFactory()

        url = reverse('core:auditlog-list')
        response = client.get(url)
        # فقط لاگ‌های کاربر فعلی باید برگردانده شود
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_list_audit_logs_unauthenticated(self, api_client):
        """
        Test listing audit logs for an unauthenticated user.
        """
        url = reverse('core:auditlog-list')
        response = api_client.get(url)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_retrieve_audit_log_authenticated(self, authenticated_api_client, AuditLogFactory):
        """
        Test retrieving a specific audit log for an authenticated user.
        """
        client, user = authenticated_api_client
        log = AuditLogFactory(user=user)

        url = reverse('core:auditlog-detail', kwargs={'pk': log.id})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(log.id)

    def test_retrieve_audit_log_other_user(self, authenticated_api_client, AuditLogFactory, CustomUserFactory):
        """
        Test retrieving a specific audit log belonging to another user (should fail).
        """
        client, user = authenticated_api_client
        other_user = CustomUserFactory()
        log = AuditLogFactory(user=other_user)

        url = reverse('core:auditlog-detail', kwargs={'pk': log.id})
        response = client.get(url)
        assert response.status_code == status.HTTP_404_NOT_FOUND # یا 403 بسته به پیاده‌سازی IsOwnerOrReadOnly

    # تست‌های POST/PUT/PATCH/DELETE معمولاً فقط برای ادمین یا در شرایط خاصی مجاز است
    # و یا اصلاً برای این مدل مجاز نیستند (ReadOnlyModelViewSet)
    # def test_create_audit_log(self, ...): # نباید مجاز باشد در ReadOnlyModelViewSet


class TestSystemSettingViewSet:
    """
    Tests for the SystemSettingViewSet.
    """
    def test_list_system_settings_admin(self, admin_api_client, SystemSettingFactory):
        """
        Test listing system settings for an admin user.
        """
        client, admin_user = admin_api_client
        SystemSettingFactory.create_batch(5)
        url = reverse('core:systemsetting-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 5

    def test_list_system_settings_non_admin(self, authenticated_api_client, SystemSettingFactory):
        """
        Test listing system settings for a non-admin user (should fail).
        """
        client, user = authenticated_api_client
        SystemSettingFactory.create_batch(5)
        url = reverse('core:systemsetting-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_system_setting_admin(self, admin_api_client, SystemSettingFactory):
        """
        Test retrieving a specific system setting for an admin user.
        """
        client, admin_user = admin_api_client
        setting = SystemSettingFactory(key='API_TIMEOUT', value='60', is_sensitive=False)
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['key'] == 'API_TIMEOUT'

    def test_retrieve_sensitive_setting_shows_masked_value(self, admin_api_client, SystemSettingFactory):
        """
        Test that retrieving a sensitive setting shows a masked value.
        """
        client, admin_user = admin_api_client
        setting = SystemSettingFactory(key='SECRET_KEY', value='very_secret_123', is_sensitive=True)
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert response.data['value'] == '***' # یا مقدار مسک شده

    def test_create_system_setting_admin(self, admin_api_client):
        """
        Test creating a system setting for an admin user.
        """
        client, admin_user = admin_api_client
        url = reverse('core:systemsetting-list')
        data = {
            'key': 'NEW_SETTING',
            'value': 'new_value',
            'data_type': 'str',
            'description': 'A new setting',
            'is_sensitive': False
        }
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert SystemSetting.objects.filter(key='NEW_SETTING').exists()

    def test_create_system_setting_non_admin(self, authenticated_api_client):
        """
        Test creating a system setting for a non-admin user (should fail).
        """
        client, user = authenticated_api_client
        url = reverse('core:systemsetting-list')
        data = {'key': 'FORBIDDEN_SETTING', 'value': 'val'}
        response = client.post(url, data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_system_setting_admin(self, admin_api_client, SystemSettingFactory):
        """
        Test updating a system setting for an admin user.
        """
        client, admin_user = admin_api_client
        setting = SystemSettingFactory(key='UPDATE_ME', value='old_value')
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        new_data = {'value': 'new_value', 'description': 'Updated description'}
        response = client.patch(url, new_data, format='json')
        assert response.status_code == status.HTTP_200_OK
        setting.refresh_from_db()
        assert setting.value == 'new_value'

    def test_update_system_setting_non_admin(self, authenticated_api_client, SystemSettingFactory):
        """
        Test updating a system setting for a non-admin user (should fail).
        """
        client, user = authenticated_api_client
        setting = SystemSettingFactory(key='UPDATE_ME', value='old_value')
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        new_data = {'value': 'new_value'}
        response = client.patch(url, new_data, format='json')
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_system_setting_admin(self, admin_api_client, SystemSettingFactory):
        """
        Test deleting a system setting for an admin user.
        """
        client, admin_user = admin_api_client
        setting = SystemSettingFactory(key='DELETE_ME', value='val')
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        response = client.delete(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not SystemSetting.objects.filter(id=setting.id).exists()

    def test_delete_system_setting_non_admin(self, authenticated_api_client, SystemSettingFactory):
        """
        Test deleting a system setting for a non-admin user (should fail).
        """
        client, user = authenticated_api_client
        setting = SystemSettingFactory(key='DELETE_ME', value='val')
        url = reverse('core:systemsetting-detail', kwargs={'pk': setting.id})
        response = client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert SystemSetting.objects.filter(id=setting.id).exists()


class TestCacheEntryViewSet:
    """
    Tests for the CacheEntryViewSet.
    """
    # این مدل ممکن است فقط برای ادمین مدیریت شود یا فقط برای خواندن
    # بسته به سیاست امنیتی
    def test_list_cache_entries_admin(self, admin_api_client, CacheEntryFactory):
        """
        Test listing cache entries for an admin user.
        """
        client, admin_user = admin_api_client
        CacheEntryFactory.create_batch(3)
        url = reverse('core:cacheentry-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 3

    def test_list_cache_entries_non_admin(self, authenticated_api_client, CacheEntryFactory):
        """
        Test listing cache entries for a non-admin user (should fail).
        """
        client, user = authenticated_api_client
        CacheEntryFactory.create_batch(3)
        url = reverse('core:cacheentry-list')
        response = client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalidate_cache_entry_admin(self, admin_api_client, CacheEntryFactory):
        """
        Test invalidating (deleting) a cache entry for an admin user.
        """
        client, admin_user = admin_api_client
        entry = CacheEntryFactory(key='test_key_to_invalidate', value='test_val')
        url = reverse('core:cacheentry-invalidate', kwargs={'pk': entry.id}) # فرض: یک اکشن سفارشی به نام invalidate تعریف شده است
        response = client.post(url)
        assert response.status_code == status.HTTP_204_NO_CONTENT # یا 200 OK با بدنه پاسخ
        assert not CacheEntry.objects.filter(id=entry.id).exists()

    def test_invalidate_cache_entry_non_admin(self, authenticated_api_client, CacheEntryFactory):
        """
        Test invalidating a cache entry for a non-admin user (should fail).
        """
        client, user = authenticated_api_client
        entry = CacheEntryFactory(key='test_key_to_invalidate', value='test_val')
        url = reverse('core:cacheentry-invalidate', kwargs={'pk': entry.id})
        response = client.post(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert CacheEntry.objects.filter(id=entry.id).exists()

# --- تست نماهای مدل BaseOwnedModel ---
# این تست‌ها باید برای هر مدلی که از BaseOwnedModel ارث می‌برد و یک ViewSet دارد، انجام شود
# مثلاً اگر مدلی مثل UserSetting در instruments از BaseOwnedModel ارث می‌برد و در instruments.views یک ViewSet دارد
# تست‌های زیر در tests/test_instruments/test_views.py قرار می‌گیرند
# اما اگر مدلی در خود core باشد، می‌تواند اینجا تست شود
# مثال فرضی: اگر یک مدل Watchlist در core بود
# class TestCoreOwnedModelViewSet:
#     def test_create_sets_owner(self, authenticated_api_client):
#         client, user = authenticated_api_client
#         url = reverse('core:coreownedmodel-list') # فرض
#         data = {'name': 'My Owned List'} # فرض فیلد name
#         response = client.post(url, data, format='json')
#         assert response.status_code == status.HTTP_201_CREATED
#         # چک کردن اینکه owner در پایگاه داده برابر user است
#         instance = CoreOwnedModel.objects.get(id=response.data['id'])
#         assert instance.owner == user
#
#     def test_update_other_users_owned_model_fails(self, authenticated_api_client, CoreOwnedModelFactory, CustomUserFactory):
#         client, user = authenticated_api_client
#         other_user = CustomUserFactory()
#         owned_instance = CoreOwnedModelFactory(owner=other_user)
#         url = reverse('core:coreownedmodel-detail', kwargs={'pk': owned_instance.id})
#         data = {'name': 'Attempted Update'}
#         response = client.put(url, data, format='json')
#         # این بستگی به اجازه‌نامه دارد. ممکن است 403 یا 404 برگرداند (اگر IsOwnerOrReadOnly باشد)
#         assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]
#         owned_instance.refresh_from_db()
#         assert owned_instance.owner == other_user # owner تغییر نکرده است

# --- تست سایر نماهای Core ---
# می‌توانید تست‌هایی برای نماهایی که در core/views.py تعریف کرده‌اید یا نیاز به آن‌ها دارید اضافه کنید
# مثلاً اگر یک نمای سفارشی برای مدیریت کاربران وجود داشت یا یک نمای سفارشی برای سلامت سیستم
# class TestCustomCoreView:
#     def test_logic(self, api_client):
#         # ...

logger.info("Core view tests loaded successfully.")
