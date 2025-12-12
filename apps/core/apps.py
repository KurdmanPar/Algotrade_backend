# apps/core/apps.py

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
import logging

logger = logging.getLogger(__name__)

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = _('Core System')

    def ready(self):
        """
        Runs when the Django application starts up.
        Imports and connects the signal handlers for this app.
        This is the recommended place to register signals.
        """
        try:
            # --- ثبت سیگنال‌ها ---
            import apps.core.signals  # noqa F401
            logger.info("Signals for 'core' app loaded successfully.")

            # --- سایر کارهای مربوط به شروع اپلیکیشن (اختیاری) ---
            # مثلاً شروع یک تاسک Celery خاص یا بارگذاری داده‌های اولیه
            # از آنجا که ممکن است نیاز به اطمینان از وجود مدل‌ها یا سرویس‌های دیگر باشد،
            # معمولاً کارهای پیچیده را در جای دیگری انجام می‌دهند (مثلاً در Celery Beat یا یک نما).
            # فقط برای موارد ساده و اولیه مناسب است.
            # logger.info("Custom startup logic for 'core' app executed.")

            # --- مثال: تنظیم کانفیگ‌های عمومی ---
            # می‌توانید از اینجا تنظیماتی که باید هنگام شروع اپلیکیشن اعمال شوند را بخوانید یا تنظیم کنید
            # مثلاً از مدل SystemSetting
            # from .models import SystemSetting
            # from django.conf import settings
            # try:
            #     global_rate_limit = SystemSetting.get_value('GLOBAL_RATE_LIMIT_PER_MINUTE', default=1000)
            #     settings.GLOBAL_RATE_LIMIT = global_rate_limit
            # except Exception as e:
            #     logger.error(f"Failed to load global settings from DB on startup: {e}")
            #     settings.GLOBAL_RATE_LIMIT = 1000 # مقدار پیش‌فرض

        except ImportError as e:
            logger.error(f"Failed to load signals for 'core' app: {e}")
            # بسته به نیاز، می‌توانید خطایی را دوباره بالا بیاورید یا فقط لاگ کنید
            # raise e

        # --- مثال: ایجاد یک مدل پایه در صورت عدم وجود (برای تست یا نصب اولیه) ---
        # این فقط در صورتی معنادار است که مدلی بسیار پایه و حیاتی نیاز به وجود داشته باشد
        # مثلاً یک گروه کاربری پیش‌فرض یا یک تنظیم اولیه
        # from .models import SystemSetting
        # SystemSetting.objects.get_or_create(
        #     key='FIRST_RUN_CHECK',
        #     defaults={'value': 'False', 'data_type': 'bool', 'description': 'Check if system has run for the first time.'}
        # )
