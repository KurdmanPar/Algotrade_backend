# apps/core/fields.py

from django.db import models
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import re

# --- فیلدهای سفارشی (Custom Fields) ---

class PriceField(models.DecimalField):
    """
    A custom DecimalField for storing financial prices.
    Enforces a fixed precision to prevent floating-point errors.
    Defaults to max_digits=20 and decimal_places=8.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_digits'] = kwargs.get('max_digits', 20)
        kwargs['decimal_places'] = kwargs.get('decimal_places', 8)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Ensures the value is converted to a Decimal.
        """
        if value is None:
            return value
        return Decimal(str(value))

    def validate(self, value, model_instance):
        """
        Validates the price value.
        """
        super().validate(value, model_instance)
        if value is not None:
            if value < 0:
                raise ValidationError(_("Price cannot be negative."), code='invalid_price_negative')
            # می‌توانید منطق دیگری مانند چک کردن حداقل/حداکثر قیمت نیز اضافه کنید
            # if value < Decimal('0.00000001'):
            #     raise ValidationError(_("Price is too small."), code='invalid_price_too_small')


class SymbolField(models.CharField):
    """
    A custom CharField for storing trading symbols.
    Enforces a specific format (e.g., ABC/XYZ, ABCXYZ).
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = kwargs.get('max_length', 32)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        """
        Converts the value to uppercase for consistency.
        """
        value = super().to_python(value)
        if value:
            return value.upper()
        return value

    def clean(self, value, model_instance):
        """
        Validates the symbol format.
        """
        value = super().clean(value, model_instance)
        if value:
            # الگو: فقط حروف بزرگ، اعداد، خط فاصله یا اسلش، بدون فاصله، طول مناسب
            pattern = r'^[A-Z0-9/_\-.]+$' # ممکن است نیاز به تغییر داشته باشد
            if not re.match(pattern, value):
                raise ValidationError(
                    _("'%(value)s' is not a valid symbol format. Must contain only uppercase letters, numbers, and separators (/ or _ or -)."),
                    code='invalid_symbol_format',
                    params={'value': value},
                )
        return value

    def validate(self, value, model_instance):
        """
        Additional validation after cleaning.
        """
        super().validate(value, model_instance)
        # می‌توانید چک‌های بیشتری مانند بررسی وجود نماد در لیست نمادهای موجود انجام دهید
        # if not is_valid_symbol_on_exchanges(value): # تابع فرضی
        #     raise ValidationError(_("Symbol '%(value)s' is not valid or supported on exchanges."), code='symbol_not_supported', params={'value': value})


class PercentageField(models.DecimalField):
    """
    A custom DecimalField for storing percentages.
    Enforces a range between 0 and 100 (or -100 to 100 if negative percentages are allowed).
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_digits'] = kwargs.get('max_digits', 8)
        kwargs['decimal_places'] = kwargs.get('decimal_places', 4)
        # اگر نیاز به درصد منفی ندارید، فقط 0 تا 100 را معتبر کنید
        # اگر نیاز دارید، min_value را -100 قرار دهید
        kwargs['validators'] = kwargs.get('validators', []) + [MinValueValidator(Decimal('-100')), MaxValueValidator(Decimal('100'))]
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        """
        Validates the percentage value.
        """
        super().validate(value, model_instance)
        if value is not None:
            if value < Decimal('-100') or value > Decimal('100'):
                raise ValidationError(_("Percentage must be between -100 and 100."), code='invalid_percentage_range')


class LeverageField(models.DecimalField):
    """
    A custom DecimalField for storing leverage values.
    Enforces a minimum value of 1.
    """
    def __init__(self, *args, **kwargs):
        kwargs['max_digits'] = kwargs.get('max_digits', 5)
        kwargs['decimal_places'] = kwargs.get('decimal_places', 2)
        kwargs['validators'] = kwargs.get('validators', []) + [MinValueValidator(Decimal('1'))]
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        """
        Validates the leverage value.
        """
        super().validate(value, model_instance)
        if value is not None:
            if value < Decimal('1'):
                raise ValidationError(_("Leverage must be at least 1."), code='invalid_leverage')


class RiskLevelField(models.CharField):
    """
    A custom CharField for storing risk levels with predefined choices.
    """
    RISK_LEVEL_CHOICES = [
        ('LOW', _('Low')),
        ('MEDIUM', _('Medium')),
        ('HIGH', _('High')),
        ('VERY_HIGH', _('Very High')),
    ]

    def __init__(self, *args, **kwargs):
        kwargs['max_length'] = 16
        kwargs['choices'] = self.RISK_LEVEL_CHOICES
        super().__init__(*args, **kwargs)

# --- فیلدهای مرتبط با امنیت ---
# مثلاً یک فیلد برای ذخیره IPها یا CIDRها (اگرچه JSONField ممکن است مناسب‌تر باشد)
class IPListField(models.TextField):
    """
    A custom TextField for storing a comma-separated list of IP addresses or CIDR blocks.
    Note: A JSONField might be more appropriate for complex lists.
    """
    def to_python(self, value):
        """
        Converts the stored string back to a list of IPs/CIDRs.
        """
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [item.strip() for item in value.split(',') if item.strip()]

    def from_db_value(self, value, expression, connection):
        """
        Converts the value from the database (usually a string) to a Python object (list).
        """
        return self.to_python(value)

    def get_prep_value(self, value):
        """
        Prepares the value for storage in the database (converts list back to string).
        """
        if not value:
            return ""
        if isinstance(value, list):
            return ",".join(value)
        return str(value)

    def validate(self, value, model_instance):
        """
        Validates the list of IPs/CIDRs using the helper function.
        """
        super().validate(value, model_instance)
        if value:
            from .helpers import validate_ip_list # import داخل تابع برای جلوگیری از حلقه
            if not validate_ip_list(self.get_prep_value(value)):
                raise ValidationError(_("One or more IP addresses or CIDR blocks are invalid."), code='invalid_ip_list')

# --- مثال: فیلد برای ذخیره داده‌های رمزنگاری شده ---
# این فقط یک مثال ساده است. برای رمزنگاری واقعی، می‌توانید از django-cryptography یا سایر کتابخانه‌ها استفاده کنید
# یا یک فیلد مشابه در helpers/encryption قرار دهید
# class EncryptedTextField(models.TextField):
#     """
#     A TextField that automatically encrypts its value before saving to the database
#     and decrypts it when retrieved.
#     Requires a global encryption key in settings.
#     """
#     def from_db_value(self, value, expression, connection):
#         if value is not None:
#             from .encryption import decrypt_field # import داخل تابع
#             return decrypt_field(value, iv=getattr(self, 'iv', '')) # IV نیز باید ذخیره شود
#         return value
#
#     def get_prep_value(self, value):
#         if value is not None:
#             from .encryption import encrypt_field # import داخل تابع
#             encrypted_val, iv = encrypt_field(value)
#             # IV را نیز در فیلد جداگانه‌ای ذخیره کنید یا در یک فیلد مشترک
#             # مثلاً اگر مدل دارای فیلد encrypted_field_iv باشد:
#             # self.model_instance.encrypted_field_iv = iv
#             return encrypted_val
#         return value
#
#     # این فیلد نیازمند یک مکانیزم ذخیره IV و دسترسی به کلید رمزنگاری است
#     # پیاده‌سازی کامل آن پیچیده‌تر است و معمولاً کتابخانه‌های خارجی استفاده می‌شوند

logger.info("Core custom fields loaded successfully.")
