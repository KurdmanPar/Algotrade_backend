# apps/instruments/helpers.py

import re
import logging
from ipaddress import ip_network, ip_address, IPv4Address, IPv6Address
from typing import List, Optional, Union
from decimal import Decimal, InvalidOperation
import hashlib
import secrets
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

logger = logging.getLogger(__name__)

# --- توابع مربوط به اعتبارسنجی و کار با داده ---
def validate_symbol_format(symbol: str) -> bool:
    """
    Validates the format of a trading symbol (e.g., BTCUSDT).
    Allows alphanumeric characters and underscores, with a reasonable length.
    Does not check for existence in the database.
    """
    if not symbol:
        return False
    # مثال: فقط حروف بزرگ، اعداد و بدون فاصله، حداقل 2 و حداکثر 20 کاراکتر
    pattern = r'^[A-Z0-9_]{2,20}$'
    return bool(re.match(pattern, symbol))

def is_valid_amount(amount: Union[str, Decimal, float, int]) -> bool:
    """
    Checks if a given value is a valid positive decimal amount.
    """
    try:
        decimal_amount = Decimal(str(amount))
        return decimal_amount > 0
    except (ValueError, TypeError, InvalidOperation):
        return False

def is_valid_price(price: Union[str, Decimal, float, int]) -> bool:
    """
    Checks if a given value is a valid positive decimal price.
    Similar to is_valid_amount but named specifically for prices.
    """
    return is_valid_amount(price)

def is_valid_quantity(quantity: Union[str, Decimal, float, int]) -> bool:
    """
    Checks if a given value is a valid positive decimal quantity/trade size.
    Similar to is_valid_amount but named specifically for quantities.
    """
    return is_valid_amount(quantity)

def validate_tick_size(price: Decimal, tick_size: Decimal) -> bool:
    """
    Validates if a price conforms to the specified tick size.
    Example: If tick_size is 0.01, then price 123.45 is valid, but 123.456 is not.
    """
    if tick_size <= 0:
        return False
    remainder = price % tick_size
    # اگر باقیمانده بسیار کوچک باشد (به دلیل دقت)، معتبر فرض می‌شود
    return remainder < tick_size / 10 # یا یک مقدار دقت مشخص


# --- توابع مربوط به مدیریت IP ---
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

def is_ip_in_allowed_list(client_ip_str: str, allowed_ips_list: List[str]) -> bool:
    """
    Checks if a client IP is within the list of allowed IPs or CIDR blocks.
    Uses the validate_ip_list function to ensure inputs are valid first.
    """
    try:
        # تأیید صحت فرمت IPهای لیست مجاز (به عنوان یک چک امنیتی اضافی)
        # اگر validate_ip_list برای لیست ورودی None برگرداند، نباید اجازه داد.
        if not validate_ip_list(','.join(allowed_ips_list)):
             logger.warning("Allowed IP list contains invalid formats.")
             return False # یا می‌توانید خطایی صادر کنید

        client_ip = ip_address(client_ip_str)
        for allowed_ip_str in allowed_ips_list:
            if '/' in allowed_ip_str: # CIDR block
                network = ip_network(allowed_ip_str, strict=False)
                if client_ip in network:
                    return True
            else: # Single IP
                allowed_ip = ip_address(allowed_ip_str)
                if client_ip == allowed_ip:
                    return True
        return False
    except ValueError as e:
        logger.error(f"Error checking IP against allowed list: {e}")
        return False # اگر IP مشتری نامعتبر بود، قطعاً مجاز نیست
    except Exception as e:
        logger.error(f"Unexpected error in is_ip_in_allowed_list: {e}")
        return False # برای امنیت، در صورت خطا، دسترسی رد می‌شود


# --- توابع امنیتی و رمزنگاری ---
def hash_sensitive_data( str) -> str:
    """
    Creates a SHA-256 hash of the input data.
    Useful for hashing sensitive data before logging or storage.
    """
    return hashlib.sha256(data.encode()).hexdigest()

def mask_sensitive_data( str, visible_chars: int = 4) -> str:
    """
    Masks sensitive data like API keys or IDs, showing only a few initial/final characters.
    Example: mask_sensitive_data('abc123def456', 3) -> 'abc...456'
    """
    if len(data) <= 2 * visible_chars:
        return data
    start = data[:visible_chars]
    end = data[-visible_chars:]
    middle = '*' * (len(data) - 2 * visible_chars)
    return f"{start}{middle}{end}"

def generate_secure_token(length: int = 32) -> str:
    """
    Generates a cryptographically secure random token.
    Suitable for API keys, session IDs, etc.
    """
    return secrets.token_urlsafe(length)


# --- توابع مربوط به کار با اعداد اعشاری و دقت ---
def round_to_tick_size(price: Decimal, tick_size: Decimal) -> Decimal:
    """
    Rounds a price to the nearest valid tick size.
    Example: round_to_tick_size(Decimal('123.456'), Decimal('0.01')) -> Decimal('123.46')
    """
    if tick_size <= 0:
        raise ValueError("Tick size must be positive.")
    # تقسیم بر tick_size
    divided = price / tick_size
    # گرد کردن به نزدیک‌ترین عدد صحیح
    rounded_divided = divided.quantize(Decimal('1'), rounding='ROUND_HALF_UP')
    # ضرب مجدد در tick_size
    return rounded_divided * tick_size


# --- توابع کمکی عمومی ---
def get_client_ip(request) -> str:
    """
    Extracts the real client IP, considering proxies (e.g., X-Forwarded-For).
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def generate_device_fingerprint(request) -> str:
    """
    Generates a simple device fingerprint based on request headers.
    This is a basic example and can be enhanced with more sophisticated techniques.
    """
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    accept_encoding = request.META.get('HTTP_ACCEPT_ENCODING', '')
    fingerprint_data = f"{user_agent}:{accept_language}:{accept_encoding}"
    return hashlib.md5(fingerprint_data.encode()).hexdigest()

def get_location_from_ip(ip: str) -> str:
    """
    Gets location information from an IP address.
    This is a placeholder. In production, you would use a service like MaxMind GeoIP2.
    """
    # مثال ساده: فقط localhost یا IPهای داخلی را تشخیص می‌دهد
    if ip.startswith('127.') or ip.startswith('10.') or ip.startswith('192.168.') or ip.startswith('172.'):
        return "Internal Network"
    # در محیط واقعی، از یک کتابخانه یا API جغرافیایی استفاده کنید
    # e.g., import geoip2.database
    # reader = geoip2.database.Reader('/path/to/GeoLite2-City.mmdb')
    # response = reader.city(ip)
    # return f"{response.city.name}, {response.country.name}"
    return "Unknown Location"

# --- توابع مربوط به داده‌های بازار ---
def normalize_data_from_source(raw_ dict, source_name: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Normalizes raw data from different data sources into a standard format.
    This function maps source-specific field names to a common structure based on the data type.
    """
    try:
        normalized = {}
        source_upper = source_name.upper()

        if data_type == 'OHLCV':
            if source_upper == 'BINANCE':
                # فرض: raw_data یک دیکشنری از یک کندل Binance است
                # [0] Open Time, [1] Open, [2] High, [3] Low, [4] Close, [5] Volume, [7] Quote Asset Volume, [8] Number of Trades
                # [9] Taker Buy Base Vol, [10] Taker Buy Quote Vol
                k = raw_data.get('k', {})
                normalized = {
                    'timestamp': k.get('T', 0), # Close time
                    'open': Decimal(str(k.get('o', 0))),
                    'high': Decimal(str(k.get('h', 0))),
                    'low': Decimal(str(k.get('l', 0))),
                    'close': Decimal(str(k.get('c', 0))),
                    'volume': Decimal(str(k.get('v', 0))),
                    'quote_volume': Decimal(str(k.get('q', 0))),
                    'number_of_trades': int(k.get('n', 0)),
                    'taker_buy_base_asset_volume': Decimal(str(k.get('V', 0))),
                    'taker_buy_quote_asset_volume': Decimal(str(k.get('Q', 0))),
                    'best_bid': Decimal(str(k.get('b', 0))) if k.get('b') else None,
                    'best_ask': Decimal(str(k.get('a', 0))) if k.get('a') else None,
                }
            elif source_upper == 'COINBASE':
                # مثال: فرض بر این است که raw_data ساختار {'time': ..., 'low': ..., 'high': ..., 'open': ..., 'close': ..., 'volume': ...} دارد
                normalized = {
                    'timestamp': int(float(raw_data['time'])),
                    'open': Decimal(str(raw_data['open'])),
                    'high': Decimal(str(raw_data['high'])),
                    'low': Decimal(str(raw_data['low'])),
                    'close': Decimal(str(raw_data['close'])),
                    'volume': Decimal(str(raw_data['volume'])),
                    'quote_volume': None, # Coinbase ممکن است جداگانه ندهد
                    'number_of_trades': None,
                    'taker_buy_base_asset_volume': None,
                    'taker_buy_quote_asset_volume': None,
                    'best_bid': None,
                    'best_ask': None,
                }
            # ... سایر صرافی‌ها ...
            else:
                logger.warning(f"No normalization logic found for source '{source_name}' and data type '{data_type}'. Raw  {raw_data}")
                return None # یا ممکن است بخواهید raw_data را همانطور برگردانید

        elif data_type == 'TICK':
            if source_upper == 'BINANCE':
                # فرض: raw_data شامل فیلدهایی مانند {'p': 'price', 'q': 'qty', 'T': 'time', 'm': 'buyer_market_maker'} است
                normalized = {
                    'timestamp': raw_data['T'],
                    'price': Decimal(raw_data['p']),
                    'quantity': Decimal(raw_data['q']),
                    'side': 'BUY' if raw_data['m'] else 'SELL', # Maker sell = Taker buy
                    'trade_id': raw_data.get('t') # ممکن است وجود نداشته باشد
                }
            # ... سایر صرافی‌ها ...
            else:
                logger.warning(f"No normalization logic found for source '{source_name}' and data type '{data_type}'. Raw  {raw_data}")
                return None

        elif data_type == 'ORDERBOOK':
            if source_upper == 'BINANCE':
                 # فرض: raw_data شامل {'bids': [...], 'asks': [...], 'T': 'time', 'U': 'first_update_id', 'u': 'final_update_id'} است
                 normalized = {
                     'timestamp': raw_data['T'],
                     'bids': [[Decimal(str(bid[0])), Decimal(str(bid[1]))] for bid in raw_data['bids']], # [[Price, Quantity], ...]
                     'asks': [[Decimal(str(ask[0])), Decimal(str(ask[1]))] for ask in raw_data['asks']],
                     'first_update_id': raw_data.get('U'),
                     'final_update_id': raw_data.get('u'),
                     'checksum': raw_data.get('checksum') # ممکن است وجود نداشته باشد
                 }
            # ... سایر صرافی‌ها ...
            else:
                 logger.warning(f"No normalization logic found for source '{source_name}' and data type '{data_type}'. Raw  {raw_data}")
                 return None
        # ... سایر انواع داده ...

        # اضافه کردن زمان پردازش
        normalized['processed_at'] = timezone.now().isoformat()

        return normalized

    except (KeyError, ValueError, TypeError, InvalidOperation) as e:
        logger.error(f"Error normalizing data from {source_name} for {data_type}: {str(e)}. Raw  {raw_data}")
        return None


def validate_ohlcv_data(data: Dict[str, Any], data_type: str = 'OHLCV') -> Optional[Dict[str, Any]]:
    """
    Validates the structure and content of normalized OHLCV data.
    Checks for logical consistency (e.g., Low <= Open <= High).
    """
    if data_type != 'OHLCV':
        return data # فقط برای OHLCV اعتبارسنجی خاص انجام می‌دهیم

    try:
        open_price = data.get('open')
        high_price = data.get('high')
        low_price = data.get('low')
        close_price = data.get('close')
        volume = data.get('volume')

        if open_price is None or high_price is None or low_price is None or close_price is None:
            raise ValueError("Missing required OHLCV fields (open, high, low, close).")

        if volume is None or volume < 0:
            raise ValueError("Volume must be a non-negative number.")

        if open_price < 0 or high_price < 0 or low_price < 0 or close_price < 0:
            raise ValueError("Prices must be non-negative.")

        # اعتبارسنجی منطق قیمت
        if low_price > open_price or open_price > high_price or low_price > close_price or close_price > high_price:
             hp = float(high_price)
             lp = float(low_price)
             op = float(open_price)
             cp = float(close_price)
             if not (lp <= op <= hp and lp <= cp <= hp):
                  raise ValueError(f"OHLCV prices are inconsistent: L:{lp} O:{op} H:{hp} C:{cp}")

        if high_price < low_price:
            raise ValueError(f"High price ({high_price}) cannot be less than Low price ({low_price}).")

        # تأیید اینکه timestamp منطقی است (مثلاً در گذشته نباشد، مگر اینکه داده تاریخی باشد)
        # این بستگی به نیاز سیستم دارد. برای مثال، فقط بررسی می‌کنیم که null نباشد.
        if data.get('timestamp') is None:
            raise ValueError("Timestamp is required.")

        return data
    except ValueError as e:
        logger.warning(f"OHLCV data validation failed: {str(e)}. Data: {data}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during OHLCV data validation: {str(e)}. Data: {data}")
        return None


# --- سایر توابع کمکی مفید ---
# مثلاً:
# - تابعی برای تبدیل واحد (مثلاً BTC به sats)
# - تابعی برای محاسبه ساده (مثلاً میانگین قیمت)
# - تابعی برای کار با رشته‌های JSON
# - تابعی برای اعتبارسنجی ساختارهای پیچیده
# - تابعی برای تولید نام فایل یا شناسه منحصر به فرد مبتنی بر زمان و داده
def generate_unique_filename(base_name: str, extension: str) -> str:
    """
    Generates a unique filename by appending a timestamp and a random suffix.
    Example: generate_unique_filename('report', '.pdf') -> 'report_20231027_123456_abc123.pdf'
    """
    timestamp = timezone.now().strftime("%Y%m%d_%H%M%S")
    random_suffix = secrets.token_hex(3) # 6 کاراکتر هگزادسیمال
    return f"{base_name}_{timestamp}_{random_suffix}.{extension.lstrip('.')}"


# --- مثال استفاده ---
# print(validate_symbol_format("BTCUSDT")) # True
# print(is_valid_amount("1.5")) # True
# print(mask_sensitive_data("my_secret_key_123", 5)) # my_se...ey_123
# print(round_to_tick_size(Decimal('123.456'), Decimal('0.01'))) # 123.46
# print(validate_ip_list("192.168.1.1,10.0.0.0/8,invalid_ip")) # None
# print(validate_ip_list("192.168.1.1,10.0.0.0/8")) # ['192.168.1.1', '10.0.0.0/8']
