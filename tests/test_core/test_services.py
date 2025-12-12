# tests/test_core/test_services.py

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.utils import timezone
from django.core.exceptions import ValidationError
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
)
from apps.core.services import (
    CoreService,
    AuditService,
    # ... سایر سرویس‌های core ...
)
from apps.core.exceptions import (
    CoreSystemException,
    DataIntegrityException,
    ConfigurationError,
    # ... سایر استثناهای core ...
)
from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
from apps.instruments.factories import InstrumentFactory # فرض بر این است که فکتوری وجود دارد
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
    # ... سایر فکتوری‌های core ...
)

pytestmark = pytest.mark.django_db

class TestCoreService:
    """
    Tests for the CoreService class.
    """
    # این سریالایزر انتزاعی است، بنابراین مستقیماً تست نمی‌شود.
    # تست‌های آن از طریق سریالایزرهایی که از آن ارث می‌برند انجام می‌شود.
    pass


class TestAuditService:
    """
    Tests for the AuditService class.
    """
    def test_log_action_creates_entry(self, CustomUserFactory):
        """
        Test that the log_action method creates an AuditLog entry.
        """
        user = CustomUserFactory(email='auditor@example.com')
        details = {'param1': 'value1', 'param2': 'value2'}
        request_mock = MagicMock()
        request_mock.META.get.return_value = '192.168.1.100'

        AuditService.log_action(
            user=user,
            action='USER_LOGIN',
            target_model_name='CustomUser',
            target_id=user.id,
            details=details,
            request=request_mock
        )

        log_entry = AuditLog.objects.get(user=user, action='USER_LOGIN')
        assert log_entry.target_model == 'CustomUser'
        assert log_entry.target_id == user.id
        assert log_entry.details == details
        assert log_entry.ip_address == '192.168.1.100'

    def test_log_action_handles_missing_request_gracefully(self, CustomUserFactory):
        """
        Test that log_action does not fail if request object is None or lacks META.
        """
        user = CustomUserFactory()
        details = {'event': 'test'}

        # فراخوانی بدون request
        AuditService.log_action(
            user=user,
            action='TEST_ACTION',
            target_model_name='CustomUser',
            target_id=user.id,
            details=details,
            request=None
        )
        # باید ورودی ایجاد شود، اما فیلدهای IP و UA خالی باشند
        log_entry = AuditLog.objects.get(user=user, action='TEST_ACTION')
        assert log_entry.ip_address is None
        assert log_entry.user_agent is None

    def test_get_user_audit_logs(self, AuditLogFactory, CustomUserFactory):
        """
        Test retrieving audit logs for a specific user.
        """
        user = CustomUserFactory()
        other_user = CustomUserFactory()
        log_for_user = AuditLogFactory(user=user, action='ACTION_1')
        log_for_other = AuditLogFactory(user=other_user, action='ACTION_2')

        logs = AuditService.get_user_audit_logs(user)

        assert log_for_user in logs
        assert log_for_other not in logs
        assert logs.count() == 1

    def test_get_user_audit_logs_filtered(self, AuditLogFactory, CustomUserFactory):
        """
        Test retrieving filtered audit logs for a user.
        """
        user = CustomUserFactory()
        log1 = AuditLogFactory(user=user, action='CREATE', target_model='Instrument')
        log2 = AuditLogFactory(user=user, action='UPDATE', target_model='Strategy')
        log3 = AuditLogFactory(user=user, action='CREATE', target_model='Order') # این باید گرفته نشود

        logs = AuditService.get_user_audit_logs(user, action_filter='CREATE', model_filter='Instrument')

        assert log1 in logs
        assert log2 not in logs
        assert log3 not in logs
        assert logs.count() == 1


# --- تست سرویس‌های دیگر در Core ---
class TestSystemSettingService:
    """
    Tests for the SystemSetting related logic within CoreService or a dedicated SettingService.
    """
    def test_get_system_setting_value(self, SystemSettingFactory):
        """
        Test retrieving a system setting value, preferably from cache.
        Falls back to database if not cached or expired.
        """
        setting = SystemSettingFactory(key='TEST_SETTING', value='test_val', data_type='str', is_active=True)

        # ابتدا فرض می‌کنیم در کش نیست، پس از DB باید بخواند
        with patch('apps.core.services.cache.get') as mock_cache_get, \
             patch('apps.core.services.cache.set') as mock_cache_set:
            mock_cache_get.return_value = None # فرض کش خالی

            retrieved_val = CoreService.get_system_setting_value('TEST_SETTING', default='default_val', use_cache=True)

            assert retrieved_val == 'test_val'
            mock_cache_set.assert_called_once_with('sys_setting_test_setting', 'test_val', timeout=3600) # timeout پیش‌فرض

    def test_get_system_setting_value_from_cache(self, SystemSettingFactory):
        """
        Test retrieving a system setting value from cache.
        """
        setting = SystemSettingFactory(key='CACHED_SETTING', value='cached_val', data_type='str', is_active=True)

        with patch('apps.core.services.cache.get') as mock_cache_get:
            mock_cache_get.return_value = 'cached_val_from_cache'

            retrieved_val = CoreService.get_system_setting_value('CACHED_SETTING', default='default_val', use_cache=True)

            assert retrieved_val == 'cached_val_from_cache'
            mock_cache_get.assert_called_once_with('sys_setting_cached_setting') # کش کی از کوئری پایین‌تر

    def test_get_system_setting_value_not_found(self, SystemSettingFactory):
        """
        Test retrieving a system setting value that does not exist.
        """
        retrieved_val = CoreService.get_system_setting_value('NON_EXISTENT_SETTING', default='default_val')

        assert retrieved_val == 'default_val'

    def test_update_system_setting(self, SystemSettingFactory):
        """
        Test creating or updating a system setting and clearing its cache.
        """
        with patch('apps.core.services.cache.delete') as mock_cache_delete:
            setting = CoreService.update_system_setting(
                key='NEW_SETTING',
                value='new_val',
                data_type='str',
                description='A new test setting.',
                is_sensitive=False
            )

            assert setting.key == 'NEW_SETTING'
            assert setting.get_parsed_value() == 'new_val'
            mock_cache_delete.assert_called_once_with('sys_setting_new_setting') # کش کی مربوطه حذف شد


class TestCacheService:
    """
    Tests for the CacheService class (اگر در core تعریف شده باشد).
    """
    def test_get_cached_value_from_external_cache(self, mocker):
        """
        Test retrieving a value from the external cache (e.g., Redis).
        """
        # Mock کردن کش خارجی
        mock_cache_get = mocker.patch('django.core.cache.cache.get')
        mock_cache_get.return_value = 'cached_value_123'

        key = 'test_key_ext'
        value = CacheService.get_cached_value(key, use_db_fallback=False)

        assert value == 'cached_value_123'
        mock_cache_get.assert_called_once_with(key)

    def test_get_cached_value_from_db_cache_fallback(self, CacheEntryFactory):
        """
        Test retrieving a value from the database cache if not found in external cache.
        """
        entry = CacheEntryFactory(key='test_key_db', value='db_cached_value', expires_at=None)
        # Mock کردن کش خارجی تا None برگرداند
        with patch('django.core.cache.cache.get') as mock_get:
            mock_get.return_value = None

            value = CacheService.get_cached_value('test_key_db', use_db_fallback=True)

            assert value == 'db_cached_value' # مقدار از پایگاه داده باید گرفته شود

    def test_get_cached_value_expired_from_db_fallback(self, CacheEntryFactory):
        """
        Test that an expired value from DB cache is not returned and is deleted.
        """
        now = timezone.now()
        expired_entry = CacheEntryFactory(
            key='test_key_expired',
            value='old_val',
            expires_at=now - timezone.timedelta(minutes=1)
        )
        # Mock کردن کش خارجی تا None برگرداند
        with patch('django.core.cache.cache.get') as mock_get:
            mock_get.return_value = None

            value = CacheService.get_cached_value('test_key_expired', use_db_fallback=True)

            assert value is None # چون منقضی شده است
            assert not CacheEntry.objects.filter(id=expired_entry.id).exists() # و حذف شده است

    def test_set_cached_value_in_external_and_db_cache(self, mocker, CacheEntryFactory):
        """
        Test setting a value in both external cache and database cache table.
        """
        mock_cache_set = mocker.patch('django.core.cache.cache.set')

        key = 'db_test_key'
        value = 'db_test_value'
        ttl = 3600

        CacheService.set_cached_value(key, value, ttl_seconds=ttl, use_db_cache=True)

        # چک کردن اینکه کش خارجی نیز ست شده است
        mock_cache_set.assert_called_once_with(key, value, timeout=ttl)

        # چک کردن اینکه ورودی DB نیز ایجاد شده است
        assert CacheEntry.objects.filter(key=key).exists()
        db_entry = CacheEntry.objects.get(key=key)
        assert db_entry.value == value
        expected_expiry = timezone.now() + timezone.timedelta(seconds=ttl)
        assert abs((db_entry.expires_at - expected_expiry).total_seconds()) < 5 # اختلاف کمتر از 5 ثانیه


# --- تست سرویس‌های دیگر ---
# می‌توانید برای سرویس‌هایی که در core/services.py تعریف می‌کنید (مثلاً یک CoreSecurityService) تست بنویسید
# مثلاً:
# class TestCoreSecurityService:
#     def test_encrypt_decrypt_field(self):
#         original_data = "secret_key_123"
#         encrypted_val, iv = CoreSecurityService.encrypt_field(original_data)
#         decrypted_val = CoreSecurityService.decrypt_field(encrypted_val, iv)
#         assert decrypted_val == original_data
#
#     def test_hash_data(self):
#         data = "sensitive_data"
#         hashed = CoreSecurityService.hash_data(data)
#         assert len(hashed) == 64 # SHA-256
#         assert hashed != data

logger.info("Core service tests loaded successfully.")
