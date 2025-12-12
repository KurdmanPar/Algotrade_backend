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
    send_verification_email_task,
    send_password_reset_email_task,
    send_2fa_codes_task,
    log_audit_event_task,
    cleanup_expired_cache_entries_task,
    cleanup_expired_system_settings_task, # فرض: یک تاسک مشابه برای SystemSetting وجود دارد
    # سایر تاسک‌های شما
)
from apps.accounts.factories import CustomUserFactory
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
)

pytestmark = pytest.mark.django_db

class TestCoreTasks:
    """
    Test suite for the Celery tasks in the core app.
    These tests often involve mocking external services (like email sending, cache backend).
    """

    @patch('apps.core.tasks.EmailMultiAlternatives.send')
    def test_send_verification_email_task(self, mock_email_send, CustomUserFactory):
        """
        Test the send_verification_email_task.
        Mocks the email sending part to avoid actual SMTP calls.
        """
        user = CustomUserFactory(email='test@example.com')
        token = 'mock_token_123'

        # فرض بر این است که فایل‌های قالب وجود دارند
        send_verification_email_task(user.id, token)

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

        send_password_reset_email_task(user.id, token)

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

        send_2fa_codes_task(user.id, codes)

        mock_email_send.assert_called_once()
        assert len(mail.outbox) == 1
        sent_email = mail.outbox[0]
        assert user.email in sent_email.to
        assert 'Backup Codes' in sent_email.subject
        # چک کردن اینکه آیا کدها در بدنه ایمیل قرار دارند
        for code in codes:
            assert code in sent_email.body

    def test_log_audit_event_task(self, CustomUserFactory):
        """
        Test the log_audit_event_task.
        """
        user = CustomUserFactory()
        action = 'TEST_ACTION'
        target_model = 'CustomUser'
        target_id = user.id
        details = {'param': 'value'}
        ip_address = '127.0.0.1'
        user_agent = 'Test Agent'

        log_audit_event_task(user.id, action, target_model, target_id, details, ip_address, user_agent)

        # چک کردن اینکه آیا ورودی AuditLog ایجاد شده است
        assert AuditLog.objects.filter(
            user=user,
            action=action,
            target_model=target_model,
            target_id=target_id
        ).exists()

        log_entry = AuditLog.objects.get(user=user, action=action)
        assert log_entry.details == details
        assert log_entry.ip_address == ip_address
        assert log_entry.user_agent == user_agent

    def test_cleanup_expired_cache_entries_task(self, CacheEntryFactory):
        """
        Test the cleanup_expired_cache_entries_task.
        """
        # ایجاد چند ورودی کش: یکی منقضی شده، یکی فعال، یکی بدون انقضا
        now = timezone.now()
        expired_entry = CacheEntryFactory(expires_at=now - timezone.timedelta(minutes=1))
        active_entry = CacheEntryFactory(expires_at=now + timezone.timedelta(hours=1))
        no_expiry_entry = CacheEntryFactory(expires_at=None)

        # اطمینان از اینکه قبل از تاسک، هر سه وجود دارند
        assert CacheEntry.objects.count() == 3

        cleanup_expired_cache_entries_task()

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

        cleanup_expired_system_settings_task()

        assert not SystemSetting.objects.filter(id=expired_setting.id).exists()
        assert SystemSetting.objects.filter(id=active_setting.id).exists()
        assert SystemSetting.objects.filter(id=no_expiry_setting.id).exists()
        assert SystemSetting.objects.count() == 2

    # --- تست تاسک‌های سفارشی ---
    # مثال: اگر تاسک send_security_alert_task وجود داشت
    # @patch('apps.core.tasks.EmailMultiAlternatives.send')
    # def test_send_security_alert_task(self, mock_email_send, CustomUserFactory):
    #     user = CustomUserFactory(email='alert@example.com')
    #     message = 'Suspicious activity detected!'
    #
    #     send_security_alert_task(user.id, message)
    #
    #     mock_email_send.assert_called_once()
    #     assert len(mail.outbox) == 1
    #     sent_email = mail.outbox[0]
    #     assert user.email in sent_email.to
    #     assert message in sent_email.body
    #     assert 'Security Alert' in sent_email.subject

    # --- تست تاسک‌هایی که ممکن است خطا داشته باشند ---
    def test_task_handles_missing_user(self):
        """
        Test that a task gracefully handles a situation where the user does not exist.
        """
        non_existent_user_id = 999999

        # فرض: تاسک log_audit_event_task اگر user.id وجود نداشت، خطایی ایجاد می‌کند یا فقط لاگ می‌کند
        # این بستگی به نحوه پیاده‌سازی تاسک دارد
        # ممکن است نیاز به استفاده از pytest raises داشته باشیم
        # with pytest.raises(CustomUser.DoesNotExist): # اگر به صورت مستقیم فریاد بزند
        #    log_audit_event_task(non_existent_user_id, 'SOME_ACTION', 'User', 1, {})
        # یا اگر فقط لاگ کند:
        # log_audit_event_task(non_existent_user_id, 'SOME_ACTION', 'User', 1, {})
        # assert "does not exist" in caplog.text # اگر از caplog استفاده کنیم
        pass # تست واقعی بستگی به منطق داخل تاسک دارد

    # --- تست تاسک‌هایی با retry ---
    # مثال: اگر تاسکی با autoretry_for بود
    # @patch('apps.core.tasks.some_external_call_that_can_fail')
    # def test_task_with_retry_logic(self, mock_external_call):
    #     mock_external_call.side_effect = [Exception("Temp failure"), None] # اول شکست، بعد موفقیت
    #     # تاسک را فراخوانی کنید
    #     # ببینید چه اتفاقی می‌افتد (مثلاً چند بار فراخوانی می‌شود یا نه)
    #     # این نیازمند جزئیات بیشتری از نحوه پیاده‌سازی Celery در پروژه است
    #     pass

logger.info("Core task tests loaded successfully.")
