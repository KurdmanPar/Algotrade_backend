###################################################################
### first Code : #################################################
###################################################################

# # apps/accounts/models.py
# from django.contrib.auth.models import AbstractUser
# from django.db import models
#
#
# class CustomUser(AbstractUser):
#     """
#     مدل کاربر سفارشی پروژه که از ایمیل به عنوان نام کاربری استفاده می‌کند.
#     """
#     username = None  # نام کاربری پیش‌فرض را غیرفعال می‌کنیم
#     email = models.EmailField(unique=True, verbose_name="Email Address")
#
#     # فیلدهای timestamp را فقط با auto_now_add و auto_now تعریف کنید
#     created_at = models.DateTimeField(auto_now_add=True)
#     updated_at = models.DateTimeField(auto_now=True)
#
#     # فیلدهای اضافی مورد نیاز
#     phone_number = models.CharField(max_length=32, blank=True)
#     is_verified = models.BooleanField(default=False)
#
#     USERNAME_FIELD = 'email'  # مشخص کردن ایمیل به عنوان فیلد ورود
#     REQUIRED_FIELDS = [] # فیلدهای مورد نیاز هنگام ایجاد سوپر یوزر
#
#     def __str__(self):
#         return self.email



###################################################################
### Second Code : #################################################
###################################################################


# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class CustomUser(AbstractUser, BaseModel):
    """
    مدل کاربر سفارشی پروژه که از ایمیل به عنوان نام کاربری استفاده می‌کند.
    مناسب برای سیستم معاملات الگوریتمی.
    """
    username = None  # غیرفعال کردن username پیش‌فرض
    email = models.EmailField(unique=True, verbose_name=_("Email Address"))

    # نام کاربری جایگزین برای نمایش عمومی
    username_display = models.CharField(
        max_length=150,
        unique=True,
        blank=True,
        null=True,
        verbose_name=_("Display Username"),
        help_text=_("A public username for the user.")
    )

    # نوع کاربر: فردی، نهادی، توسعه‌دهنده
    USER_TYPE_CHOICES = [
        ('individual', _('Individual')),
        ('institutional', _('Institutional')),
        ('developer', _('Developer')),
    ]
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='individual',
        verbose_name=_("User Type")
    )

    # وضعیت‌های کاربر
    is_verified = models.BooleanField(default=False, verbose_name=_("Is Email Verified"))
    is_active = models.BooleanField(default=True, verbose_name=_("Is Active"))
    is_locked = models.BooleanField(default=False, verbose_name=_("Is Account Locked"))

    # زمان ایجاد و بروزرسانی حساب
    # این فیلدها از BaseModel ارث می‌بریم: created_at, updated_at

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("Custom User")
        verbose_name_plural = _("Custom Users")


class UserProfile(BaseModel):
    """
    پروفایل تکمیلی کاربر برای ذخیره اطلاعات شخصی، تماس، امنیت و تنظیمات معاملاتی.
    """
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="profile",
        verbose_name=_("User")
    )

    # اطلاعات شخصی
    first_name = models.CharField(max_length=128, blank=True, verbose_name=_("First Name"))
    last_name = models.CharField(max_length=128, blank=True, verbose_name=_("Last Name"))
    display_name = models.CharField(max_length=128, blank=True, verbose_name=_("Display Name"))
    phone_number = models.CharField(max_length=32, blank=True, verbose_name=_("Phone Number"))

    # تنظیمات مرتبط با امنیت
    two_factor_enabled = models.BooleanField(default=False, verbose_name=_("Two-Factor Authentication Enabled"))
    api_access_enabled = models.BooleanField(default=False, verbose_name=_("API Access Enabled"))
    max_api_requests_per_minute = models.IntegerField(default=1000, verbose_name=_("Max API Requests Per Minute"))

    # تنظیمات مرتبط با معاملات
    preferred_base_currency = models.CharField(
        max_length=16,
        default="IRT",  # تغییر از USD به IRT
        verbose_name=_("Preferred Base Currency")
    )
    default_leverage = models.IntegerField(default=1, verbose_name=_("Default Leverage"))
    risk_level = models.CharField(
        max_length=20,
        choices=[
            ('low', _('Low Risk')),
            ('medium', _('Medium Risk')),
            ('high', _('High Risk')),
        ],
        default='medium',
        verbose_name=_("Risk Level")
    )
    max_active_trades = models.IntegerField(default=5, verbose_name=_("Max Active Trades"))

    # تنظیمات اعلان
    notify_on_trade = models.BooleanField(default=True, verbose_name=_("Notify on Trade Execution"))
    notify_on_balance_change = models.BooleanField(default=True, verbose_name=_("Notify on Balance Change"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    def __str__(self):
        return f"{self.user.email} Profile"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")