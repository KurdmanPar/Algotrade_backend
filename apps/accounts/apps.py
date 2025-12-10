# apps/accounts/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = _('Accounts')

    def ready(self):
        """
        Runs when the Django application starts up.
        Imports and connects the signal handlers for this app.
        """
        try:
            # ثبت سیگنال‌ها برای این اپلیکیشن
            import apps.accounts.signals  # noqa F401
            logger.info("Signals for 'accounts' app loaded successfully.")
        except ImportError as e:
            logger.error(f"Failed to load signals for 'accounts' app: {e}")
            # بسته به نیاز، می‌توانید خطایی را دوباره بالا بیاورید یا فقط لاگ کنید
            # raise e
