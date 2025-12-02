# apps/core/apps.py
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _
from django.contrib import admin
import logging

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """
    اپلیکیشن Core - مرکز تنظیمات و کانفیگ‌های سراسری سیستم
    این اپلیکیشن باید اولین اپلیکیشن در INSTALLED_APPS باشد
    """
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    verbose_name = _("Core System")

    def ready(self):
        """
        این متد هنگام لود شدن اپلیکیشن core اجرا می‌شود.
        تمام تنظیمات global و سراسری اینجا قرار می‌گیرند تا یکبار و مرکزی اجرا شوند.
        این بهترین practice برای جلوگیری از repetition و race condition در جنگو است.
        """

        # ============================================
        # تنظیمات Global پنل ادمین - فقط اینجا و یکبار
        # ============================================
        admin.site.site_title = _("Signal Trading Admin")
        admin.site.site_header = _("Algorithmic Trading System Administration")
        admin.site.index_title = _("Dashboard")

        logger.info("Core app loaded with centralized admin configuration")

# ============================================
# نکات امنیتی و بهینه‌سازی:
# ============================================
# 1. این فایل فقط در یک اپلیکیشن (core) قرار می‌گیرد نه همه اپلیکیشن‌ها
# 2. ready() فقط یکبار برای هر اپلیکیشن در lifecycle جنگو اجرا می‌شود
# 3. قرار دادن اینجا از circular import در signals.apps جلوگیری می‌کند
# 4. logging شروع به کار را برای مانیتورینگ سیستم ضبط می‌کند