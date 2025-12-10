# apps/exchanges/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class ExchangesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.exchanges'
    verbose_name = _('Exchanges')

    def ready(self):
        """
        Runs when the Django application starts up.
        Imports and connects the signal handlers for this app.
        """
        try:
            # ثبت سیگنال‌ها برای این اپلیکیشن
            import apps.exchanges.signals  # noqa F401
            logger.info("Signals for 'exchanges' app loaded successfully.")
        except ImportError as e:
            logger.error(f"Failed to load signals for 'exchanges' app: {e}")
            # بسته به نیاز، می‌توانید خطایی را دوباره بالا بیاورید یا فقط لاگ کنید
            # raise e

        # می‌توانید سایر کارهای مربوط به راه‌اندازی اپلیکیشن را در اینجا انجام دهید
        # مثلاً شروع یک تاسک Celery خاص یا بارگذاری داده‌های اولیه
        # اما باید مراقب باشید که کارهای سنگین در اینجا باعث کند شدن راه‌اندازی شوند
