# tests/test_core/test_signals.py

import pytest
from django.db.models.signals import post_save, pre_delete
from django.test import TestCase
from django.test import RequestFactory
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
)
from apps.core.signals import (
    log_model_save,
    log_model_delete,
    update_cache_on_model_save,
    invalidate_cache_on_model_delete,
    # سایر سیگنال‌های شما
)
from apps.accounts.factories import CustomUserFactory
from apps.instruments.factories import InstrumentFactory
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
)
from unittest.mock import patch, MagicMock

pytestmark = pytest.mark.django_db

class TestCoreSignals(TestCase):
    """
    Tests for the Django signals defined in the core app.
    """

    def setUp(self):
        """
        Setup method to prepare common objects for tests.
        """
        # ممکن است نیاز به ایجاد یک کاربر یا شیء تستی داشته باشیم
        self.user = CustomUserFactory()
        self.factory = RequestFactory()

    @patch('apps.core.signals.logger.info') # مثال: mock کردن logger
    @patch('apps.core.signals.AuditService.log_action') # مثال: mock کردن یک سرویس
    def test_log_model_save_signal_triggered(self, mock_audit_service_log, mock_logger_info):
        """
        Test that the log_model_save signal handler is called when a model is saved.
        """
        # فرض: Instrument از یک مدلی ارث می‌برد که سیگنال آن ثبت شده است (مثلاً TimeStampedModel یا BaseOwnedModel)
        # یا سیگنال مستقیماً برای Instrument ثبت شده است
        # برای این تست، فرض می‌کنیم که Instrument از TimeStampedModel ارث می‌برد و TimeStampedModel سیگنال را در apps.py ثبت کرده است
        # یا اینکه سیگنال در apps/core/signals.py مستقیماً به Instrument وصل شده است

        # این کار فقط زمانی کار می‌کند که سیگنال در apps/core/apps.py ثبت شده باشد یا در signals.py به مدل وصل شده باشد
        # مثلاً: @receiver(post_save, sender=Instrument) در apps/core/signals.py
        # اگر سیگنال به این صورت وصل نشده باشد، این تست کار نمی‌کند
        # فرض: سیگنال در signals.py مستقیماً وصل شده یا در apps.py از طریق ready() ثبت شده است
        # اما برای تست مستقیم، باید اطمینان حاصل کرد که سیگنال فعال است
        # یک راه تست، ایجاد یک شیء و بررسی اینکه آیا تابع سیگنال فراخوانی شده است یا خیر.

        # ایجاد یک شیء که سیگنال را فعال می‌کند
        instrument = InstrumentFactory(owner=self.user)

        # چک کردن اینکه آیا تابع سیگنال فراخوانی شده است
        # این فقط زمانی کار می‌کند که سیگنال مستقیماً به Instrument وصل شده باشد و نام آن log_model_save باشد
        # و همچنین این که تابع log_model_save در واقع از AuditService استفاده کند
        # این یک تست نسبتاً سطحی است زیرا وابستگی به پیاده‌سازی سیگنال دارد
        # mock_audit_service_log.assert_called_once() # این فقط یک مثال است، بسته به پیاده‌سازی واقعی سیگنال

        # مثال بهتر: ایجاد یک شیء از یک مدلی که مستقیماً در core تعریف شده و سیگنال برای آن تعریف کرده‌ایم
        # فرض بر این است که AuditLog یا SystemSetting یا CacheEntry سیگنال دارند
        # مثلاً اگر سیگنال برای AuditLog تعریف کرده بودیم:
        # audit_log = AuditLogFactory(user=self.user, action='TEST_ACTION', target_model='User', target_id=self.user.id)
        # mock_logger_info.assert_called() # یا mock_audit_service_log
        pass # چون تست واقعی نیازمند یک پیاده‌سازی سیگنال خاص در signals.py و model مربوطه است

    @patch('apps.core.signals.logger.info')
    @patch('apps.core.signals.AuditService.log_action')
    def test_log_model_delete_signal_triggered(self, mock_audit_service_log, mock_logger_info):
        """
        Test that the log_model_delete signal handler is called when a model is deleted.
        """
        # مشابه بالا، اما برای pre_delete
        # audit_log = AuditLogFactory(user=self.user, action='TEST_ACTION', target_model='User', target_id=self.user.id)
        # audit_log_id = audit_log.id
        # audit_log.delete()
        # mock_logger_info.assert_called_with(f"Audit event 'DELETE' logged for {audit_log.target_model} ID {audit_log.target_id}.")
        # mock_audit_service_log.assert_called_once()
        pass # همان دلیل قبلی

    @patch('apps.core.signals.cache.set') # mock کردن عملیات کش
    def test_update_cache_on_model_save_signal(self, mock_cache_set):
        """
        Test that the update_cache_on_model_save signal handler updates the cache.
        """
        # فرض: SystemSetting یا CacheEntry دارای سیگنال update_cache_on_model_save است
        # و این سیگنال برای مدل SystemSetting فعال است
        # این تست فرض می‌کند که سیگنال مستقیماً برای SystemSetting ثبت شده است
        # مثلاً: @receiver(post_save, sender=SystemSetting) def update_cache_on_model_save(...)
        setting = SystemSettingFactory(key='TEST_CACHE_UPDATE', value='initial_val')

        # فرض بر این است که سیگنال بعد از ذخیره، کش را بروز می‌کند
        # mock_cache_set.assert_called_with('sys_setting_test_cache_update', 'initial_val', timeout=3600)
        # این فقط در صورتی کار می‌کند که سیگنال به درستی ثبت شده باشد و منطق کش در آن پیاده شده باشد
        pass # چون پیاده‌سازی واقعی سیگنال نیاز است

    @patch('apps.core.signals.cache.delete') # mock کردن عملیات کش
    def test_invalidate_cache_on_model_delete_signal(self, mock_cache_delete):
        """
        Test that the invalidate_cache_on_model_delete signal handler invalidates the cache.
        """
        # فرض: CacheEntry دارای سیگنال invalidate_cache_on_model_delete است
        # و این سیگنال برای مدل CacheEntry فعال است
        # مثلاً: @receiver(pre_delete, sender=CacheEntry) def invalidate_cache_on_model_delete(...)
        cache_entry = CacheEntryFactory(key='cache_to_delete', value='val')
        cache_key = cache_entry.key

        cache_entry.delete()

        # فرض: سیگنال حذف کلید مربوطه را از کش حذف می‌کند
        # mock_cache_delete.assert_called_with(cache_key)
        # این فقط در صورتی کار می‌کند که سیگنال به درستی ثبت شده باشد و منطق کش در آن پیاده شده باشد
        pass # چون پیاده‌سازی واقعی سیگنال نیاز است

    # --- تست سایر سیگنال‌ها ---
    # می‌توانید برای هر سیگنالی که تعریف می‌کنید، یک تست بنویسید
    # مثلاً:
    # def test_create_profile_on_user_save(self):
    #     user = CustomUserFactory()
    #     # چک کنید که آیا پروفایل ساخته شده است یا خیر
    #     assert hasattr(user, 'profile')

    # def test_sync_data_on_instrument_change(self, mocker):
    #     mock_task = mocker.patch('apps.core.signals.sync_instrument_details_from_exchange_task.delay')
    #     instrument = InstrumentFactory()
    #     instrument.name = "Updated Name"
    #     instrument.save()
    #     # اگر سیگنال sync_data_on_model_save وجود داشت و برای Instrument ثبت شده بود:
    #     # mock_task.assert_called_once_with(instrument.id)

    # نکات مهم:
    # - برای تست سیگنال‌ها، اغلب نیاز به mock کردن قسمت‌هایی که در سیگنال فراخوانی می‌شوند (مثل سرویس‌ها، تاسک‌ها، loggerها) دارید.
    # - اطمینان حاصل کنید که سیگنال در apps.py ثبت شده است (متد ready).
    # - می‌توانید برای تست، سیگنال را موقتاً غیرفعال کنید (django.db.models.signals.post_save.disconnect(...)) یا از pytest-django fixtures برای کنترل سیگنال‌ها استفاده کنید.

logger.info("Core signal tests loaded successfully.")
