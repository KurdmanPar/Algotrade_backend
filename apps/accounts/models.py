# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class CustomUserManager(BaseUserManager):
    """
    Custom User Manager where email is the unique identifier
    for authentication instead of usernames.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a regular user with the given email and password.
        """
        if not email:
            raise ValueError(_("The Email must be set"))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a superuser with the given email and password.
        """
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError(_("Superuser must have is_staff=True."))
        if extra_fields.get("is_superuser") is not True:
            raise ValueError(_("Superuser must have is_superuser=True."))

        return self.create_user(email, password, **extra_fields)




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
    is_demo = models.BooleanField(default=True, verbose_name=_("Is Demo Account"))

    # اطلاعات امنیتی
    failed_login_attempts = models.PositiveIntegerField(default=0, verbose_name=_("Failed Login Attempts"))
    locked_until = models.DateTimeField(null=True, blank=True, verbose_name=_("Account Locked Until"))
    last_login_ip = models.GenericIPAddressField(null=True, blank=True, verbose_name=_("Last Login IP"))
    last_login_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Last Login At"))

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = _("Custom User")
        verbose_name_plural = _("Custom Users")

    # اعمال مانیجر سفارشی
    objects = CustomUserManager()


class UserProfile(BaseModel):
    """
    پروفایل تکمیلی کاربر برای ذخیره اطلاعات شخصی، تماس، امنیت، معاملات و تنظیمات کاربری.
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
    nationality = models.CharField(max_length=64, blank=True, verbose_name=_("Nationality"))
    date_of_birth = models.DateField(null=True, blank=True, verbose_name=_("Date of Birth"))
    address = models.TextField(blank=True, verbose_name=_("Address"))

    # تنظیمات مرتبط با امنیت
    two_factor_enabled = models.BooleanField(default=False, verbose_name=_("Two-Factor Authentication Enabled"))
    api_access_enabled = models.BooleanField(default=False, verbose_name=_("API Access Enabled"))
    max_api_requests_per_minute = models.IntegerField(default=1000, verbose_name=_("Max API Requests Per Minute"))
    allowed_ips = models.TextField(
        blank=True,
        verbose_name=_("Allowed IPs"),
        help_text=_("Comma separated list of IPs allowed to access the API.")
    )

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
    max_capital = models.DecimalField(
        max_digits=16,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name=_("Maximum Allowed Capital (Demo/Real)")
    )

    # تنظیمات اعلان
    notify_on_trade = models.BooleanField(default=True, verbose_name=_("Notify on Trade Execution"))
    notify_on_balance_change = models.BooleanField(default=True, verbose_name=_("Notify on Balance Change"))
    notify_on_risk_limit_breach = models.BooleanField(default=True, verbose_name=_("Notify on Risk Limit Breach"))

    # تنظیمات مربوط به AML/KYC
    is_kyc_verified = models.BooleanField(default=False, verbose_name=_("Is KYC Verified"))
    kyc_document_type = models.CharField(max_length=32, blank=True, verbose_name=_("KYC Document Type"))
    kyc_document_number = models.CharField(max_length=64, blank=True, verbose_name=_("KYC Document Number"))
    kyc_submitted_at = models.DateTimeField(null=True, blank=True, verbose_name=_("KYC Submitted At"))
    kyc_verified_at = models.DateTimeField(null=True, blank=True, verbose_name=_("KYC Verified At"))

    # فیلدهای timestamp از BaseModel ارث می‌بریم: created_at, updated_at

    def __str__(self):
        return f"{self.user.email} Profile"

    class Meta:
        verbose_name = _("User Profile")
        verbose_name_plural = _("User Profiles")