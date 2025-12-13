# tests/test_core/test_tasks.py

import pytest
from unittest.mock import patch, MagicMock
from django.core import mail
from django.utils import timezone
from decimal import Decimal
from apps.core.models import (
    AuditLog,
    SystemSetting,
    CacheEntry,
)
from apps.core.tasks import (
    log_audit_event_task,
    send_verification_email_task,
    send_password_reset_email_task,
    send_2fa_codes_task,
    cleanup_expired_cache_entries_task,
    cleanup_expired_system_settings_task,
    # سایر تاسک‌های شما
)
from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
)
from apps.core.exceptions import (
    CoreSystemException,
    DataIntegrityException,
    ConfigurationError,
    # سایر استثناهای شما
)

pytestmark = pytest.mark.django_db

class TestCoreTasks:
    """
    Test suite for the Celery tasks defined in apps/core/tasks.py.
    These tests often involve mocking external services (like email sending, cache backend).
    """

    @patch('apps.core.tasks.AuditService.log_event') # فرض بر این است که AuditService وجود دارد
    def test_log_audit_event_task_calls_service(self, mock_audit_service_log, CustomUserFactory):
        """
        Test that the log_audit_event_task correctly calls the AuditService.
        """
        user = CustomUserFactory()
        action = 'USER_LOGIN'
        target_model_name = 'CustomUser'
        target_id = user.id
        details = {'ip': '127.0.0.1'}
        ip_address = '127.0.0.1'
        user_agent = 'Test-Agent'

        log_audit_event_task.delay(
            user_id=user.id,
            action=action,
            target_model_name=target_model_name,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent
        )

        mock_audit_service_log.assert_called_once_with(
            user=user,
            action=action,
            target_model_name=target_model_name,
            target_id=target_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            request=None # چون request در تاسک وجود ندارد
        )

    @patch('apps.core.tasks.EmailMultiAlternatives.send')
    def test_send_verification_email_task(self, mock_email_send, CustomUserFactory):
        """
        Test the send_verification_email_task.
        Mocks the email sending part to avoid actual SMTP calls.
        """
        user = CustomUserFactory(email='test@example.com')
        token = 'mock_token_123'

        send_verification_email_task.delay(user.id, token)

        # چک کردن اینکه آیا تابع ارسال ایمیل فراخوانی شده است
        mock_email_send.assert_called_once()
        # چک کردن اینکه آیا ایمیل به آدرس صحیح ارسال شده است
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert user.email in sent_email.to
        assert 'Verify your email' in sent_email.subject

    @patch('apps.core.tasks.EmailMultiAlternatives.send')
    def test_send_password_reset_email_task(self, mock_email_send, CustomUserFactory):
        """
        Test the send_password_reset_email_task.
        """
        user = CustomUserFactory(email='reset@example.com')
        token = 'reset_token_456'

        send_password_reset_email_task.delay(user.id, token)

        mock_email_send.assert_called_once()
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert user.email in sent_email.to
        assert 'Reset your password' in sent_email.subject

    @patch('apps.core.tasks.EmailMultiAlternatives.send')
    def test_send_2fa_codes_task(self, mock_email_send, CustomUserFactory):
        """
        Test the send_2fa_codes_task.
        """
        user = CustomUserFactory(email='2fa@example.com')
        codes = ['CODE1234', 'CODE5678']

        send_2fa_codes_task.delay(user.id, codes)

        mock_email_send.assert_called_once()
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert user.email in sent_email.to
        assert 'Backup Codes' in sent_email.subject
        # چک کردن اینکه آیا کدها در بدنه ایمیل قرار دارند
        for code in codes:
            assert code in sent_email.body

    @patch('django.core.cache.cache.delete')
    def test_invalidate_cache_key_task(self, mock_cache_delete):
        """
        Test the invalidate_cache_key_task.
        """
        key = 'test_cache_key_to_invalidate'

        invalidate_cache_key_task.delay(key)

        # چک کردن حذف از کش خارجی
        mock_cache_delete.assert_called_once_with(key)

        # اطمینان از اینکه ورودی DB نیز حذف شده است
        assert not CacheEntry.objects.filter(key=key).exists()

    def test_cleanup_expired_cache_entries_task(self, CacheEntryFactory):
        """
        Test the cleanup_expired_cache_entries_task.
        """
        now = timezone.now()
        # ایجاد چند ورودی کش: یکی منقضی شده، یکی فعال، یکی بدون انقضا
        expired_entry = CacheEntryFactory(expires_at=now - timezone.timedelta(minutes=1))
        active_entry = CacheEntryFactory(expires_at=now + timezone.timedelta(hours=1))
        no_expiry_entry = CacheEntryFactory(expires_at=None)

        # اطمینان از اینکه قبل از تاسک، هر سه وجود دارند
        assert CacheEntry.objects.count() == 3

        cleanup_expired_cache_entries_task.delay()

        # چک کردن اینکه فقط ورودی منقضی شده حذف شده است
        assert not CacheEntry.objects.filter(id=expired_entry.id).exists()
        assert CacheEntry.objects.filter(id=active_entry.id).exists()
        assert CacheEntry.objects.filter(id=no_expiry_entry.id).exists()
        assert CacheEntry.objects.count() == 2

    def test_cleanup_expired_system_settings_task(self, SystemSettingFactory):
        """
        Test the cleanup_expired_system_settings_task (assumes it exists and works similarly to cache).
        """
        # فرض: SystemSetting نیز فیلد expires_at دارد
        now = timezone.now()
        expired_setting = SystemSettingFactory(expires_at=now - timezone.timedelta(minutes=1))
        active_setting = SystemSettingFactory(expires_at=now + timezone.timedelta(hours=1))
        no_expiry_setting = SystemSettingFactory(expires_at=None)

        assert SystemSetting.objects.count() == 3

        cleanup_expired_system_settings_task.delay()

        assert not SystemSetting.objects.filter(id=expired_setting.id).exists()
        assert SystemSetting.objects.filter(id=active_setting.id).exists()
        assert SystemSetting.objects.filter(id=no_expiry_setting.id).exists()
        assert SystemSetting.objects.count() == 2

    # --- تست تاسک‌هایی که ممکن است خطا داشته باشند ---
    def test_task_handles_missing_user(self, caplog):
        """
        Test that a task gracefully handles a situation where the user does not exist.
        """
        non_existent_user_id = 999999

        # فرض: تاسک log_audit_event_task اگر user.id وجود نداشت، خطایی ایجاد می‌کند یا فقط لاگ می‌کند
        with caplog.at_level(logging.ERROR):
            log_audit_event_task.delay(
                user_id=non_existent_user_id,
                action='SOME_ACTION',
                target_model_name='User',
                target_id=1,
                details={},
                ip_address='127.0.0.1',
                user_agent='Test-Agent'
            )

        # چک کردن اینکه آیا خطایی در لاگ ثبت شده است
        assert "User with id 999999 does not exist" in caplog.text # یا متن دقیق پیام خطا
        # یا اینکه فقط چک می‌کنیم که خطا رخ نداده (اگر خطای وجود نداشتن کاربر در تاسک مدیریت شود)
        # assert "error" not in caplog.text

    def test_task_handles_missing_cache_entry_for_invalidation(self, caplog):
        """
        Test that invalidate_cache_key_task gracefully handles a missing cache entry in DB.
        """
        key = 'non_existent_cache_key'
        assert not CacheEntry.objects.filter(key=key).exists()

        with caplog.at_level(logging.WARNING): # یا INFO بسته به نحوه لاگ در تاسک
            invalidate_cache_key_task.delay(key)

        # چک کردن اینکه آیا پیام مناسب در لاگ چاپ شده است
        # این فقط زمانی معنی دارد که تاسک در صورت عدم وجود ورودی DB، چیزی را لاگ کند
        # assert f"No DB cache entry found for key '{key}' to invalidate." in caplog.text
        # در تاسک ما، فقط کش خارجی حذف می‌شود. اگر ورودی DB وجود نداشت، هیچ کاری نمی‌کند و خطایی نمی‌دهد.
        # بنابراین، لاگ ممکن است فقط در صورتی ایجاد شود که ورودی DB وجود داشته و حذف شده باشد.
        # از آنجا که ورودی وجود نداشت، فقط کش خارجی حذف می‌شود و هیچ خروجی خطا نمی‌دهد.
        # پس این تست فقط در صورتی معنی دارد که تاسک منطقی برای لاگ کردن عدم وجود DB داشته باشد.
        # در اینجا، فقط چک می‌کنیم که تاسک بدون خطا اجرا شود.
        # assert "No DB cache entry found" in caplog.text # فقط اگر تاسک این لاگ را داشت

    # --- تست تاسک‌هایی با retry ---
    # مثال: اگر تاسکی با autoretry_for بود
    # @patch('apps.core.tasks.some_external_call_that_can_fail')
    # def test_task_with_retry_logic(self, mock_external_call):
    #     mock_external_call.side_effect = [Exception("Temp failure"), None] # اول شکست، بعد موفقیت
    #     # تاسک را فراخوانی کنید
    #     # task_instance = some_task_with_retry.signature(args=[...]).apply()
    #     # assert mock_external_call.call_count == 2 # یک بار اول اجرا، یک بار دوباره
    #     pass # تست واقعی نیازمند جزئیات پیاده‌سازی Celery در پروژه است

# --- تست سایر تاسک‌های Core ---
# می‌توانید برای سایر تاسک‌هایی که در apps/core/tasks.py تعریف می‌کنید نیز تست بنویسید
# مثلاً اگر تاسکی برای مدیریت کاربران وجود داشت:
# class TestUserManagementTasks:
#     def test_something(self):
#         # ...

logger.info("Core task tests loaded successfully.")
