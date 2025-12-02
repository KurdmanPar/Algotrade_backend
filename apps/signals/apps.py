# apps/signals/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)


class SignalsConfig(AppConfig):
    """
    اپلیکیشن Signal Management - مدیریت سیگنال‌های معاملاتی
    این اپلیکیشن وابسته به core است و باید بعد از آن در INSTALLED_APPS قرار گیرد
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.signals'
    verbose_name = _("Signal Management")

    def ready(self):
        """
        این متد هنگام لود شدن اپلیکیشن signals اجرا می‌شود.
        برای اتصال به سیگنال‌های Django (event handlers) و لاگینگ startup.
        """

        # ============================================
        # اتصال سیگنال‌های Django برای Audit Trail
        # این import باید داخل ready() باشد نه بالای فایل
        # برای جلوگیری از circular import و Models not loaded yet error
        # ============================================
        try:
            import apps.signals.signals  # noqa: F401
            logger.info("Signal event handlers connected successfully")
        except ImportError as e:
            logger.error(f"Failed to import signals handlers: {e}")

        # ============================================
        # لاگینگ startup برای مانیتورینگ و امنیت
        # ============================================
        logger.info("Signals app loaded successfully")

# ============================================
# نکات پیاده‌سازی:
# ============================================
# 1. فایل apps/signals/signals.py باید وجود داشته باشد (در زیر توضیح داده شده)
# 2. این اپلیکیشن باید بعد از 'apps.core' در INSTALLED_APPS قرار گیرد
# 3. verbose_name برای نمایش در ادمین استفاده می‌شود
# 4. ready() برای هر worker/thread یکبار اجرا می‌شود