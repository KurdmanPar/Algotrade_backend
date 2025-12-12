# tests/test_core/test_logging.py

import pytest
import logging
from io import StringIO
from django.test import override_settings
from django.contrib.auth import get_user_model
from apps.core.models import AuditLog
from apps.core.logging import (
    AuditLogger,
    get_logger,
    log_sensitive_action,
    # سایر اجزای logging
)
from apps.accounts.factories import CustomUserFactory
from apps.core.factories import AuditLogFactory

User = get_user_model()

pytestmark = pytest.mark.django_db

class TestAuditLogger:
    """
    Tests for the AuditLogger custom logging handler.
    """
    @pytest.fixture
    def log_capture(self):
        """
        Fixture to capture log records.
        """
        log_capture_string = StringIO()
        handler = logging.StreamHandler(log_capture_string)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger('apps.core.logging') # یا نام لاگری که AuditLogger به آن اضافه شده است
        logger.addHandler(handler)
        yield log_capture_string
        logger.removeHandler(handler)

    def test_emit_creates_audit_log_entry(self, mocker, CustomUserFactory):
        """
        Test that the AuditLogger's emit method creates an AuditLog entry in the database.
        """
        user = CustomUserFactory()
        mock_record = mocker.MagicMock()
        mock_record.msg = "Test audit message"
        mock_record.levelname = "INFO"
        mock_record.name = "apps.core.test"
        mock_record.user = user # این فیلد باید توسط Middleware یا Context اضافه شود
        mock_record.ip_address = '192.168.1.100'
        mock_record.session_key = 'test_session_abc123'
        mock_record.funcName = 'test_function'
        mock_record.lineno = 123

        audit_handler = AuditLogger()
        audit_handler.emit(mock_record)

        # چک کردن اینکه یک ورودی AuditLog ایجاد شده است
        assert AuditLog.objects.filter(
            user=user,
            action='LOG_INFO',
            details__contains={'message': 'Test audit message'},
            ip_address='192.168.1.100'
        ).exists()

    def test_emit_handles_missing_user_gracefully(self, mocker, caplog):
        """
        Test that the handler gracefully handles a log record without a user.
        """
        mock_record = mocker.MagicMock()
        mock_record.msg = "Audit message without user"
        mock_record.levelname = "WARNING"
        # mock_record.user = None # فیلد user وجود ندارد
        # این فیلد باید از context گرفته شود، و اگر وجود نداشت، باید با مقدار مناسب (مثلاً None) ذخیره شود
        # در واقع، این منطق باید در سرویس یا middleware که لاگ را ایجاد می‌کند، اعمال شود
        # AuditLogger فقط می‌خواند و ذخیره می‌کند
        # بنابراین، این تست بیشتر نشان می‌دهد که منطق داخل emit باید null-safety داشته باشد
        # اگر `getattr(record, 'user', None)` استفاده شود، باید به درستی کار کند
        # mock_record.__dict__ = {'msg': '...', 'levelname': '...', 'user': None, ...}
        mock_record.user = None
        mock_record.ip_address = None
        mock_record.session_key = None
        mock_record.funcName = 'test_func'
        mock_record.lineno = 456

        audit_handler = AuditLogger()
        # فرض: این خطا را مدیریت می‌کند و فقط لاگ می‌کند یا ورودی با user=null ایجاد می‌کند
        # اگر خطا دهد، تست ناموفق است مگر اینکه منطق مدیریت خطا داشته باشد
        audit_handler.emit(mock_record)

        # چک کردن اینکه یک ورودی ایجاد شده است، اما user آن null است
        log_entry = AuditLog.objects.filter(action='LOG_WARNING').first()
        assert log_entry is not None
        assert log_entry.user is None


class TestGetLogger:
    """
    Tests for the get_logger helper function.
    """
    def test_get_logger_returns_instance(self):
        """
        Test that get_logger returns a configured logger instance.
        """
        logger_name = 'test.logger.core'
        logger = get_logger(logger_name)

        assert isinstance(logger, logging.Logger)
        assert logger.name == logger_name
        # چک کردن اینکه آیا Handler اختصاصی (AuditLogger) اضافه شده است یا خیر
        # این فقط زمانی معنی دارد که log_to_db=True باشد
        audit_handlers = [h for h in logger.handlers if isinstance(h, AuditLogger)]
        assert len(audit_handlers) == 0 # چون log_to_db=False پیش‌فرض است
        # اگر log_to_db=True بود:
        # assert len(audit_handlers) > 0

    def test_get_logger_with_db_logging(self, mocker):
        """
        Test that get_logger adds the AuditLogger handler when log_to_db=True.
        """
        logger_name = 'test.logger.db'
        logger = get_logger(logger_name, log_to_db=True)

        audit_handlers = [h for h in logger.handlers if isinstance(h, AuditLogger)]
        assert len(audit_handlers) == 1


class TestLogSensitiveAction:
    """
    Tests for the log_sensitive_action helper function.
    """
    def test_log_sensitive_action_creates_audit_log(self, CustomUserFactory, mocker):
        """
        Test that the log_sensitive_action function creates an AuditLog entry.
        """
        user = CustomUserFactory()
        action = 'API_KEY_RETRIEVAL'
        target_model_name = 'APICredential'
        target_id = 12345
        details = {'credential_type': 'read_only'}

        mock_request = mocker.MagicMock()
        mock_request.META.get.return_value = '192.168.1.101'

        log_sensitive_action(user, action, target_model_name, target_id, details, mock_request)

        assert AuditLog.objects.filter(
            user=user,
            action=action,
            target_model=target_model_name,
            target_id=target_id,
            details=details,
            ip_address='192.168.1.101'
        ).exists()

    def test_log_sensitive_action_without_request(self, CustomUserFactory):
        """
        Test that the function works even if request object is None.
        """
        user = CustomUserFactory()
        action = 'PROFILE_UPDATE'
        target_model_name = 'UserProfile'
        target_id = user.profile.id
        details = {'changed_fields': ['first_name', 'last_name']}

        log_sensitive_action(user, action, target_model_name, target_id, details, request=None)

        log_entry = AuditLog.objects.get(
            user=user,
            action=action,
            target_model=target_model_name,
            target_id=target_id
        )
        assert log_entry.details == details
        # IP باید None باشد
        assert log_entry.ip_address is None

# --- تست سایر ابزارهای لاگ ---
# اگر کلاس‌های یا توابع دیگری برای لاگ‌گذاری در core تعریف کرده‌اید، تست‌های مربوطه را نیز اینجا بنویسید
# مثلاً اگر یک TraceIdFilter وجود داشت:
# class TestTraceIdFilter:
#     def test_filter_adds_trace_id(self):
#         # ...

logger.info("Core logging tests loaded successfully.")
