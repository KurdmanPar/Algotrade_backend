# apps/exchanges/helpers.py

import re
from decimal import Decimal
from typing import Dict, Any, List, Optional
from ipaddress import ip_network, ip_address
import logging
import hashlib
import secrets

logger = logging.getLogger(__name__)

def validate_exchange_response(response: Dict[str, Any], response_type: str) -> Dict[str, Any]:
    """
    Validates the structure and content of an API response from an exchange.
    Logs warnings or errors based on the validation results.
    """
    # اعتبارسنجی ساختار کلی (مثلاً وجود فیلدهای خاص)
    if not isinstance(response, dict):
        logger.error(f"Invalid response format: Expected dict, got {type(response)} for {response_type}")
        raise ValueError(f"Invalid response format for {response_type}")

    # مثال: اعتبارسنجی پاسخ سفارش
    if response_type == 'order_response':
        required_fields = ['id', 'symbol', 'side', 'type', 'status', 'price', 'amount']
        for field in required_fields:
            if field not in response:
                logger.warning(f"Missing field '{field}' in order response: {response}")

    # مثال: اعتبارسنجی موجودی
    elif response_type == 'balances':
        if not isinstance(response, list):
            logger.error(f"Invalid balances format: Expected list, got {type(response)}")
            raise ValueError("Invalid balances format")
        for balance_item in response:
            if not isinstance(balance_item, dict):
                logger.error(f"Invalid balance item format: {balance_item}")
                continue
            required_fields = ['asset', 'total', 'available']
            for field in required_fields:
                if field not in balance_item:
                    logger.warning(f"Missing field '{field}' in balance item: {balance_item}")

    # مثال: اعتبارسنجی اطلاعات حساب
    elif response_type == 'account_info':
        # می‌توانید فیلدهای مورد نیاز خاص خود را بررسی کنید
        pass

    # اگر اعتبارسنجی موفقیت‌آمیز بود، داده را برگردان
    return response

def is_valid_symbol(symbol: str) -> bool:
    """
    Checks if a given string is a potentially valid trading symbol.
    Example: BTCUSDT, ETH/USD
    """
    # یک الگوی ساده برای نمادها (می‌تواند پیچیده‌تر شود)
    pattern = r'^[A-Z0-9]{2,}(/[A-Z0-9]{2,})?$'
    return bool(re.match(pattern, symbol))

def is_valid_amount(amount: Any) -> bool:
    """
    Checks if a given value is a valid positive decimal amount.
    """
    try:
        decimal_amount = Decimal(str(amount))
        return decimal_amount > 0
    except (ValueError, TypeError):
        return False

def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
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

def hash_data( str) -> str:
    """
    Creates a SHA-256 hash of the input data.
    Useful for hashing sensitive data before logging or storage.
    """
    return hashlib.sha256(data.encode()).hexdigest()

def generate_secure_token(length: int = 32) -> str:
    """
    Generates a cryptographically secure random token.
    """
    return secrets.token_urlsafe(length)

# مثال استفاده:
# print(mask_sensitive_data("my_secret_api_key_12345", 5)) # -> my_se...2345
