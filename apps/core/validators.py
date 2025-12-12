# apps/core/validators.py

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from decimal import Decimal
import re
import logging

logger = logging.getLogger(__name__)

def validate_symbol_format( str) -> bool:
    """
    Validates the format of a trading symbol (e.g., BTCUSDT, ETH/USD).
    Allows alphanumeric characters, underscores, slashes, and hyphens. Max length 32.
    Does not check for existence in the database.
    """
    if not symbol:
        return False
    # الگو: حروف بزرگ، اعداد، زیرخط، اسلش، خط فاصله، بدون فاصله، طول مناسب
    pattern = r'^[A-Z0-9_/\-]{2,32}$'
    return bool(re.match(pattern, symbol))

def validate_amount_format( str) -> bool:
    """
    Validates the format of an amount string (e.g., '1.23456789').
    Checks if it's a valid positive decimal number string.
    """
    if not amount_str:
        return False
    try:
        amount = Decimal(amount_str)
        return amount > 0
    except (ValueError, TypeError):
        return False

def validate_price_format( str) -> bool:
    """
    Validates the format of a price string (e.g., '50000.00').
    Checks if it's a valid positive decimal number string.
    """
    return validate_amount_format(price_str) # قیمت مانند مقدار است، مثبت و عدد اعشاری

def validate_quantity_format( str) -> bool:
    """
    Validates the format of a quantity string (e.g., '0.12345678').
    Checks if it's a valid positive decimal number string.
    """
    return validate_amount_format(quantity_str) # مقدار مانند مقدار دیگر است، مثبت و عدد اعشاری

# --- اعتبارسنجی‌های مرتبط با IP ---
def validate_ip_list(ip_list_str: str) -> Optional[List[str]]:
    """
    Validates a comma-separated string of IP addresses or CIDR blocks.
    Returns a list of valid IPs/CIDRs or None if invalid format is found.
    """
    if not ip_list_str:
        return []
    try:
        ip_list = [item.strip() for item in ip_list_str.split(',')]
        validated_ips = []
        for ip_str in ip_list:
            if not ip_str: # اگر رشته خالی بود، نادیده گرفته شود
                continue
            if '/' in ip_str: # CIDR block
                ip_network(ip_str, strict=False) # Raises ValueError if invalid
                validated_ips.append(ip_str)
            else: # Single IP
                ip_address(ip_str) # Raises ValueError if invalid
                validated_ips.append(ip_str)
        return validated_ips
    except ValueError as e:
        logger.error(f"Invalid IP/CIDR format in list: {ip_list_str}, Error: {e}")
        return None

# --- اعتبارسنجی‌های مرتبط با داده ---
def validate_decimal_precision(value: Decimal, max_digits: int, decimal_places: int) -> bool:
    """
    Validates if a Decimal value adheres to max_digits and decimal_places constraints.
    """
    try:
        value_str = str(value)
        if '.' in value_str:
            integer_part, fractional_part = value_str.split('.')
            integer_digits = len(integer_part.lstrip('-')) # حذف علامت منفی برای شمارش
            fractional_digits = len(fractional_part)
        else:
            integer_digits = len(value_str.lstrip('-'))
            fractional_digits = 0

        if integer_digits + fractional_digits > max_digits:
            logger.warning(f"Decimal value {value} exceeds max digits {max_digits}.")
            return False
        if fractional_digits > decimal_places:
            logger.warning(f"Decimal value {value} exceeds decimal places {decimal_places}.")
            return False
        return True
    except Exception as e:
        logger.error(f"Error validating decimal precision for {value}: {str(e)}")
        return False

def validate_percentage(value: Decimal) -> bool:
    """
    Validates if a value is a valid percentage (0 <= value <= 100).
    """
    try:
        if 0 <= value <= 100:
            return True
        else:
            logger.warning(f"Percentage value {value} is not between 0 and 100.")
            return False
    except (ValueError, TypeError):
        logger.error(f"Error validating percentage {value}: Not a valid number.")
        return False

# --- اعتبارسنجی‌های مرتبط با کاربر ---
def validate_username_format( str) -> bool:
    """
    Validates the format of a username.
    e.g., alphanumeric, underscore, min/max length.
    """
    if not username:
        return False
    pattern = r'^[a-zA-Z0-9_]{3,30}$'
    return bool(re.match(pattern, username))

def validate_phone_number_format( str) -> bool:
    """
    Validates the format of a phone number (simple example).
    e.g., +1234567890
    """
    if not phone_number:
        return False
    pattern = r'^\+\d{10,15}$' # فرض: شماره با + شروع می‌شود و 10 تا 15 عدد دارد
    return bool(re.match(pattern, phone_number))

# --- اعتبارسنجی‌های مرتبط با فایل ---
def validate_file_extension_and_size(file, allowed_extensions: List[str], max_size_mb: int) -> bool:
    """
    Validates a file's extension and size.
    """
    import os
    ext = os.path.splitext(file.name)[1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"File extension '{ext}' is not allowed. Allowed extensions are: {allowed_extensions}")

    size_mb = file.size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValidationError(f"File size {size_mb:.2f}MB exceeds the maximum allowed size of {max_size_mb}MB.")
    return True

# --- کلاس‌های اعتبارسنجی جنگو ---
class SymbolValidator:
    """
    Django validator class for symbol fields.
    """
    def __call__(self, value):
        if not validate_symbol_format(value):
            raise ValidationError(
                _('Enter a valid symbol format (alphanumeric, _, /, -, max 32 chars).'),
                code='invalid_symbol_format'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)


class AmountValidator:
    """
    Django validator class for amount/price/quantity fields.
    """
    def __call__(self, value):
        if not validate_amount_format(str(value)):
            raise ValidationError(
                _('Enter a valid positive decimal amount.'),
                code='invalid_amount_format'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)

class PercentageValidator:
    """
    Django validator class for percentage fields.
    """
    def __call__(self, value):
        if not validate_percentage(value):
            raise ValidationError(
                _('Enter a valid percentage between 0 and 100.'),
                code='invalid_percentage'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)

class IPListValidator:
    """
    Django validator class for IP list fields (comma-separated string).
    """
    def __call__(self, value):
        if not validate_ip_list(value):
            raise ValidationError(
                _('Enter a valid comma-separated list of IP addresses or CIDR blocks.'),
                code='invalid_ip_list'
            )

    def __eq__(self, other):
        return isinstance(other, self.__class__)

# --- مثال: اعتبارسنجی فیلد مدل با استفاده از کلاس ---
# در models.py:
# from django.core.validators import MinValueValidator
# from apps.core.validators import SymbolValidator, AmountValidator
# class SomeModel(models.Model):
#     symbol = models.CharField(max_length=32, validators=[SymbolValidator()])
#     price = models.DecimalField(max_digits=20, decimal_places=8, validators=[MinValueValidator(0), AmountValidator()])
#     # ... سایر فیلدها
