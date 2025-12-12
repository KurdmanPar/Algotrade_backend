# apps/core/logging.py

import logging
from django.conf import settings
from django.utils import timezone
from .models import AuditLog # فرض بر این است که مدل وجود دارد
from .helpers import get_client_ip # فرض بر این است که تابع وجود دارد

# --- کلاس‌های لاگر سفارشی ---

class AuditLogger(logging.Handler):
    """
    A logging handler that writes log records to the AuditLog model in the database.
    Useful for persisting critical system events, security logs, or user actions for compliance.
    """
    def emit(self, record):
        """
        Writes the log record to the AuditLog model.
        """
        try:
            # تبدیل سطح لاگ جنگو به سطح متناظر در AuditLog (اگر مدل AuditLog چنین فیلدی داشته باشد)
            log_level_map = {
                logging.DEBUG: 'DEBUG',
                logging.INFO: 'INFO',
                logging.WARNING: 'WARNING',
                logging.ERROR: 'ERROR',
                logging.CRITICAL: 'CRITICAL',
            }
            audit_level = log_level_map.get(record.levelno, 'INFO')

            # سعی در گرفتن کاربر و IP از record (اگر توسط Middleware یا Context اضافه شده باشد)
            user = getattr(record, 'user', None)
            ip_address = getattr(record, 'ip_address', None)
            session_key = getattr(record, 'session_key', None)
            request_path = getattr(record, 'request_path', None)

            # ایجاد ورودی AuditLog
            AuditLog.objects.create(
                user=user,
                action=f"LOG_{record.levelname.upper()}",
                target_model=getattr(record, 'target_model', 'System'),
                target_id=getattr(record, 'target_id', None),
                details={
                    'logger_name': record.name,
                    'message': record.getMessage(),
                    'module': record.module,
                    'func_name': record.funcName,
                    'line_no': record.lineno,
                    'exception_info': str(record.exc_info) if record.exc_info else None,
                    'pathname': record.pathname,
                    'request_path': request_path,
                },
                ip_address=ip_address,
                user_agent=getattr(record, 'user_agent', ''),
                session_key=session_key,
            )
        except Exception:
            # در صورت بروز خطا در ذخیره در دیتابیس، فقط خطا را چاپ کن یا به روش دیگری گزارش دهید
            self.handleError(record) # این متد داخلی logging.Handler است

def get_logger(name: str, log_to_db: bool = False) -> logging.Logger:
    """
    Returns a configured logger instance with optional database audit logging.
    """
    logger = logging.getLogger(name)

    if log_to_db and not any(isinstance(handler, AuditLogger) for handler in logger.handlers):
        # اضافه کردن Handler اختصاصی AuditLogger اگر قبلاً اضافه نشده باشد
        audit_handler = AuditLogger()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        audit_handler.setFormatter(formatter)
        logger.addHandler(audit_handler)
        logger.setLevel(logging.INFO) # یا سطح مورد نظر

    return logger

# --- تابع کمکی برای لاگ اکشن‌های حساس ---
def log_sensitive_action(user, action: str, target_model: str, target_id, details: dict = None, request=None):
    """
    Logs a sensitive action performed by a user to the database audit log.
    Optionally extracts IP and User-Agent from the request object.
    """
    details = details or {}
    ip_addr = get_client_ip(request) if request else None
    ua = request.META.get('HTTP_USER_AGENT', '') if request else None
    session_key = getattr(request, 'session', {}).get('session_key', '') if request else ''

    AuditLog.objects.create(
        user=user,
        action=action,
        target_model=target_model,
        target_id=target_id,
        details=details,
        ip_address=ip_addr,
        user_agent=ua,
        session_key=session_key,
    )
    # لاگ هم در فایل/کنسول
    logger = get_logger(__name__)
    logger.warning(f"Sensitive action '{action}' performed by user {user.email} on {target_model} ID {target_id}.")

# --- مثال: استفاده از لاگر ---
# logger = get_logger(__name__, log_to_db=True)
# logger.info("User logged in successfully.", extra={'user': request.user, 'ip_address': get_client_ip(request)})
