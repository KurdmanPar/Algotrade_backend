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
        This is the recommended place to register signals.
        """
        try:
            # --- ثبت سیگنال‌ها ---
            import apps.exchanges.signals  # noqa F401
            logger.info("Signals for 'exchanges' app loaded successfully.")

            # --- سایر کارهای مربوط به شروع اپلیکیشن (اختیاری و با احتياط) ---
            # مثلاً بارگذاری داده‌های اولیه یا شروع یک تاسک اولیه (که معمولاً نیازمند تایم‌اوت یا اجرا در پس‌زمینه است)
            # از انجام کارهای سنگین در اینجا خودداری کنید، زیرا ممکن است راه‌اندازی پروژه را کند کند
            # self.start_initial_sync_if_needed() # مثال: فقط اگر کار خیلی سبک بود

        except ImportError as e:
            logger.error(f"Failed to load signals for 'exchanges' app: {e}")
            # بسته به نیاز، می‌توانید خطایی را دوباره بالا بیاورید یا فقط لاگ کنید
            # raise e

    # مثال: متدی برای انجام یک کار سبک در زمان شروع (اگر لازم باشد)
    # def start_initial_sync_if_needed(self):
    #     """
    #     Checks for pending syncs and schedules initial tasks.
    #     This is a placeholder and should be implemented carefully.
    #     """
    #     from apps.exchanges.models import ExchangeAccount
    #     from apps.exchanges.tasks import sync_exchange_account_task
    #     # این کار ممکن است بسیار زمان‌بر باشد، بنابراین باید با دقت انجام شود
    #     # مثلاً فقط برای حساب‌هایی که last_sync_at خیلی قدیمی است
    #     # یا فقط یک نشانه برای اجرای یک کار پس‌زمینه (مثل یک تاسک Celery یا یک Command مدیریتی) قرار دهید
    #     # و این کار را در ready() انجام ندهید
    #     pending_accounts = ExchangeAccount.objects.filter(
    #         is_active=True,
    #         last_sync_at__isnull=True # یا last_sync_at < timezone.now() - timedelta(hours=24)
    #     )
    #     for account in pending_accounts:
    #         # sync_exchange_account_task.delay(account.id) # نه در ready!
    #         pass # فقط یک نشانه در دیتابیس یا کش قرار دهید
    #     logger.info(f"Scheduled initial sync check for {pending_accounts.count()} accounts.")

    # مثال: متدی برای بارگذاری تنظیمات پیش‌فرض از کش یا پایگاه داده
    # def load_defaults(self):
    #     """
    #     Loads default settings for the app into memory or cache.
    #     """
    #     from apps.core.models import SystemSetting
    #     from django.core.cache import cache
    #     # بارگذاری یک یا چند تنظیم پیش‌فرض که ممکن است در طول کار اپلیکیشن مکرراً نیاز شود
    #     # cache.set('exch_defaults', SystemSetting.objects.filter(key__startswith='EXCH_').values('key', 'value'), timeout=3600)

logger.info("Exchanges app config loaded successfully.")
