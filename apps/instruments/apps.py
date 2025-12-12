# apps/instruments/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class InstrumentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.instruments'
    verbose_name = _('Instruments')

    def ready(self):
        """
        Runs when the Django application starts up.
        Imports and connects the signal handlers for this app.
        This is the recommended place to register signals.
        """
        try:
            # --- ثبت سیگنال‌ها ---
            import apps.instruments.signals  # noqa F401
            logger.info("Signals for 'instruments' app loaded successfully.")

            # --- سایر کارهای مربوط به شروع اپلیکیشن (اختیاری) ---
            # مثلاً شروع یک تاسک Celery خاص هنگام راه‌اندازی
            # از آنجا که ممکن است نیاز به اطمینان از وجود مدل‌ها یا سرویس‌های دیگر باشد،
            # معمولاً کارهای پیچیده را در جای دیگری انجام می‌دهند (مثلاً در Celery Beat یا یک نما).
            # فقط برای موارد ساده و اولیه مناسب است.
            # logger.info("Custom startup logic for 'instruments' app executed.")

        except ImportError as e:
            logger.error(f"Failed to load signals for 'instruments' app: {e}")
            # بسته به نیاز، می‌توانید خطایی را دوباره بالا بیاورید یا فقط لاگ کنید
            # raise e
