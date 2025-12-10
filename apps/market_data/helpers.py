# apps/market_data/helpers.py

import logging
from decimal import Decimal
from typing import Dict, Any, List, Optional
from django.utils import timezone
from datetime import datetime
from .exceptions import DataProcessingError

logger = logging.getLogger(__name__)

def normalize_data_from_source(raw_data: Dict[str, Any], source_name: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Normalizes raw data from different sources (e.g., Binance, Coinbase) into a standard format.
    This function maps source-specific field names to a common structure based on the data type.
    """
    normalized = {}
    try:
        if data_type == 'OHLCV':
            # مثال نرمالایز برای OHLCV از Binance
            if source_name.upper() == 'BINANCE':
                # [0] Open Time
                # [1] Open Price
                # [2] High Price
                # [3] Low Price
                # [4] Close Price
                # [5] Volume
                # [6] Close Time
                # [7] Quote Asset Volume
                # [8] Number of Trades
                # [9] Taker Buy Base Asset Volume
                # [10] Taker Buy Quote Asset Volume
                # [11] Ignore
                kline = raw_data['k'] # فرض بر این است که raw_data شامل یک کلید 'k' است که داده kline را دارد
                normalized = {
                    'timestamp': int(kline[0]),
                    'open': Decimal(str(kline[1])),
                    'high': Decimal(str(kline[2])),
                    'low': Decimal(str(kline[3])),
                    'close': Decimal(str(kline[4])),
                    'volume': Decimal(str(kline[5])),
                    'close_time': int(kline[6]),
                    'quote_volume': Decimal(str(kline[7])),
                    'number_of_trades': int(kline[8]),
                    'taker_buy_base_asset_volume': Decimal(str(kline[9])),
                    'taker_buy_quote_asset_volume': Decimal(str(kline[10])),
                    'additional_data': {} # می‌توانید داده‌های دیگر را در اینجا اضافه کنید
                }
            elif source_name.upper() == 'COINBASE':
                # مثال نرمالایز برای OHLCV از Coinbase (ساختار متفاوت)
                # فرض بر این است که raw_data ساختار زیر را دارد: {'time': ..., 'low': ..., 'high': ..., 'open': ..., 'close': ..., 'volume': ...}
                normalized = {
                    'timestamp': int(raw_data['time']),
                    'open': Decimal(str(raw_data['open'])),
                    'high': Decimal(str(raw_data['high'])),
                    'low': Decimal(str(raw_data['low'])),
                    'close': Decimal(str(raw_data['close'])),
                    'volume': Decimal(str(raw_data['volume'])),
                    'close_time': None, # Coinbase ممکن است close_time جداگانه ندهد
                    'quote_volume': None,
                    'number_of_trades': None,
                    'taker_buy_base_asset_volume': None,
                    'taker_buy_quote_asset_volume': None,
                    'additional_data': {}
                }
            # ... سایر صرافی‌ها

        elif data_type == 'TICK':
            # مثال نرمالایز برای TICK از Binance
            if source_name.upper() == 'BINANCE':
                # فرض بر این است که raw_data شامل فیلدهای tick است
                # مثلاً {'p': 'price', 'q': 'quantity', 'T': 'timestamp', 'm': 'maker', 's': 'symbol'}
                normalized = {
                    'timestamp': int(raw_data['T']),
                    'price': Decimal(str(raw_data['p'])),
                    'quantity': Decimal(str(raw_data['q'])),
                    'side': 'BUY' if raw_data['m'] else 'SELL', # maker sell = taker buy
                    'trade_id': raw_data.get('t', None)
                }
            # ... سایر صرافی‌ها

        elif data_type == 'ORDER_BOOK':
            # مثال نرمالایز برای ORDER BOOK از Binance
            if source_name.upper() == 'BINANCE':
                # فرض بر این است که raw_data شامل bids و asks است
                # مثلاً {'bids': [[price1, qty1], [price2, qty2]], 'asks': [...], 'T': 'timestamp', 'U': 'update_id', 'u': 'final_update_id'}
                normalized = {
                    'timestamp': int(raw_data['T']),
                    'bids': [[Decimal(str(bid[0])), Decimal(str(bid[1]))] for bid in raw_data['bids']],
                    'asks': [[Decimal(str(ask[0])), Decimal(str(ask[1]))] for ask in raw_data['asks']],
                    'sequence': raw_data.get('u'), # final update id
                    'checksum': raw_data.get('checksum') # ممکن است وجود نداشته باشد
                }
            # ... سایر صرافی‌ها

        # اضافه کردن منطق نرمالایز برای سایر data_typeها (INDEX, FUNDING_RATE, etc.)

        return normalized

    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error normalizing data from {source_name} for {data_type}: {str(e)}. Raw data: {raw_data}")
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

        if low_price > open_price or open_price > high_price or low_price > close_price or close_price > high_price:
            raise ValueError(f"OHLCV prices are inconsistent: Low({low_price}) <= Open({open_price}) <= High({high_price}), Low({low_price}) <= Close({close_price}) <= High({high_price}).")

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


def convert_timestamp_ms_to_datetime(timestamp_ms: int) -> datetime:
    """
    Converts a Unix timestamp in milliseconds to a timezone-aware datetime object.
    """
    try:
        dt = timezone.datetime.fromtimestamp(timestamp_ms / 1000.0)
        return timezone.make_aware(dt)
    except (ValueError, TypeError) as e:
        logger.error(f"Error converting timestamp {timestamp_ms} to datetime: {str(e)}")
        raise DataProcessingError(f"Invalid timestamp: {timestamp_ms}")


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


def hash_data(data: str) -> str:
    """
    Creates a SHA-256 hash of the input data.
    Useful for hashing sensitive data before logging or storage.
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()

# سایر توابع کمکی می‌توانند اضافه شوند
# مثلاً:
# - تابعی برای تبدیل واحد (مثلاً BTC به sats)
# - تابعی برای محاسبه ساده (مثلاً میانگین قیمت)
# - تابعی برای کار با رشته‌های JSON
# - تابعی برای اعتبارسنجی ساختارهای پیچیده
