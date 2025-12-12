# tests/test_core/test_cache.py

import pytest
from django.core.cache import cache
from django.utils import timezone
from decimal import Decimal
from apps.core.models import CacheEntry
from apps.core.cache import CacheService # فرض بر این است که کلاس CacheService وجود دارد
from apps.core.helpers import mask_sensitive_data # فرض بر این است که تابع mask وجود دارد

pytestmark = pytest.mark.django_db

class TestCacheService:
    """
    Tests for the CacheService class.
    """
    def test_get_cached_value_from_external_cache(self, mocker):
        """
        Test retrieving a value from the external cache (e.g., Redis).
        """
        # Mock کردن کش خارجی
        mock_cache_get = mocker.patch('django.core.cache.cache.get')
        mock_cache_get.return_value = 'cached_value_123'

        key = 'test_key_ext'
        value = CacheService.get_cached_value(key)

        assert value == 'cached_value_123'
        mock_cache_get.assert_called_once_with(key)

    def test_get_cached_value_from_db_cache_fallback(self, CacheEntryFactory):
        """
        Test retrieving a value from the database cache if not found in external cache.
        """
        # اطمینان از اینکه کش خارجی None برمی‌گرداند (یا کش خارجی را غیرفعال کنید در تست)
        # یا مستقیماً فقط متد get_cached_value از DB را تست کنید
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

    def test_set_cached_value_in_external_cache(self, mocker):
        """
        Test setting a value in the external cache (e.g., Redis).
        """
        mock_cache_set = mocker.patch('django.core.cache.cache.set')

        key = 'new_test_key'
        value = 'new_test_value'
        ttl = 1800

        CacheService.set_cached_value(key, value, ttl_seconds=ttl, use_db_cache=False)

        mock_cache_set.assert_called_once_with(key, value, timeout=ttl)

    def test_set_cached_value_in_db_cache(self, mocker):
        """
        Test setting a value in the database cache table.
        """
        # Mock کردن کش خارجی
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
        # assert db_entry.expires_at == ... (چون تایم‌زون ممکن است متفاوت باشد، بهتر است اختلاف زمان را چک کنیم)
        expected_expiry = timezone.now() + timezone.timedelta(seconds=ttl)
        assert abs((db_entry.expires_at - expected_expiry).total_seconds()) < 5 # اختلاف کمتر از 5 ثانیه

    def test_invalidate_cached_value(self, CacheEntryFactory, mocker):
        """
        Test invalidating (deleting) a cache key from both external and DB cache.
        """
        mock_cache_delete = mocker.patch('django.core.cache.cache.delete')

        entry = CacheEntryFactory(key='key_to_delete', value='val')
        key = entry.key

        CacheService.invalidate_cached_value(key, delete_db_entry=True)

        # چک کردن حذف از کش خارجی
        mock_cache_delete.assert_called_once_with(key)
        # چک کردن حذف از کش DB
        assert not CacheEntry.objects.filter(key=key).exists()

    def test_bulk_invalidate_cached_values(self, CacheEntryFactory, mocker):
        """
        Test invalidating multiple cache keys at once.
        """
        mock_cache_delete_many = mocker.patch('django.core.cache.cache.delete_many')

        keys_to_delete = ['key1', 'key2', 'key3']
        entries = CacheEntryFactory.create_batch(3)
        for i, entry in enumerate(entries):
             entry.key = keys_to_delete[i]
             entry.save()

        CacheService.bulk_invalidate_cached_values(keys_to_delete, delete_db_entries=True)

        # چک کردن حذف از کش خارجی
        mock_cache_delete_many.assert_called_once_with(keys_to_delete)
        # چک کردن حذف از کش DB
        assert not CacheEntry.objects.filter(key__in=keys_to_delete).exists()

    def test_get_or_set_with_function_cache_hit(self, mocker):
        """
        Test get_or_set_with_function when value is already in cache.
        """
        func_mock = mocker.MagicMock(return_value="calculated_value")
        mock_cache_get = mocker.patch('django.core.cache.cache.get', return_value="cached_value")

        result = CacheService.get_or_set_with_function('test_key', func_mock, ttl=60)

        assert result == "cached_value"
        func_mock.assert_not_called() # تابع نباید فراخوانی شود چون کش وجود داشت
        mock_cache_get.assert_called_once_with('test_key')

    def test_get_or_set_with_function_cache_miss(self, mocker):
        """
        Test get_or_set_with_function when value is not in cache.
        """
        calculated_return = "newly_calculated"
        func_mock = mocker.MagicMock(return_value=calculated_return)
        mock_cache_get = mocker.patch('django.core.cache.cache.get', return_value=None)
        mock_cache_set = mocker.patch('django.core.cache.cache.set')

        result = CacheService.get_or_set_with_function('missed_key', func_mock, ttl=120)

        assert result == calculated_return
        func_mock.assert_called_once() # تابع باید یک بار فراخوانی شود
        mock_cache_set.assert_called_once_with('missed_key', calculated_return, timeout=120) # TTL 120


class TestCacheEntryModel:
    """
    Tests for the CacheEntry model's methods.
    """
    def test_get_cached_value(self, CacheEntryFactory):
        """
        Test the get_cached_value class method.
        """
        entry = CacheEntryFactory(key='model_test_key', value='model_cached_val', expires_at=None)
        retrieved_val = CacheEntry.get_cached_value('model_test_key')
        assert retrieved_val == 'model_cached_val'

    def test_get_cached_value_expired(self, CacheEntryFactory):
        """
        Test the get_cached_value class method with an expired entry.
        """
        now = timezone.now()
        expired_entry = CacheEntryFactory(
            key='expired_key',
            value='old_val',
            expires_at=now - timezone.timedelta(seconds=1)
        )
        retrieved_val = CacheEntry.get_cached_value('expired_key')
        assert retrieved_val is None
        # ورودی باید حذف شده باشد
        assert not CacheEntry.objects.filter(id=expired_entry.id).exists()

    def test_set_cached_value(self):
        """
        Test the set_cached_value class method.
        """
        CacheEntry.set_cached_value('new_model_key', 'new_model_val', ttl_seconds=60)
        entry = CacheEntry.objects.get(key='new_model_key')
        assert entry.value == 'new_model_val'
        assert entry.expires_at is not None

    def test_is_expired(self, CacheEntryFactory):
        """
        Test the is_expired instance method.
        """
        now = timezone.now()
        active_entry = CacheEntryFactory(expires_at=now + timezone.timedelta(hours=1))
        expired_entry = CacheEntryFactory(expires_at=now - timezone.timedelta(hours=1))
        no_expiry_entry = CacheEntryFactory(expires_at=None)

        assert not active_entry.is_expired()
        assert expired_entry.is_expired()
        assert not no_expiry_entry.is_expired()

    def test_str_representation(self, CacheEntryFactory):
        """
        Test the __str__ representation of CacheEntry.
        """
        entry = CacheEntryFactory(key='repr_test_key')
        assert str(entry) == "Cache: repr_test_key"

# --- تست توابع کمکی مرتبط با کش ---
class TestCacheHelpers:
    """
    Tests for cache-related helper functions (if any exist in helpers.py).
    For example, a function to generate cache keys.
    """
    def test_generate_cache_key(self):
        """
        Test the generate_cache_key function from helpers.
        """
        # فرض بر این است که این تابع وجود دارد
        # from apps.core.helpers import generate_cache_key
        # key = generate_cache_key('instrument', 'BTCUSDT', '1m_ohlcv')
        # assert key == 'instrument_BTCUSDT_1m_ohlcv'
        pass # فقط نمونه، اگر تابع وجود داشت، تست می‌کردیم

logger.info("Core cache tests loaded successfully.")
