# apps/exchanges/helpers.py

import re
import logging
from decimal import Decimal, InvalidOperation
from typing import Dict, Any, List, Optional, Union
from ipaddress import ip_network, ip_address, IPv4Address, IPv6Address
from django.utils import timezone
import hashlib
import secrets
import json
import struct
from apps.core.helpers import (
    get_client_ip,
    generate_device_fingerprint,
    mask_sensitive_data,
    validate_ip_list, # import از core.helpers
)
from apps.core.exceptions import (
    CoreSystemException,
    DataIntegrityException,
    # اگر نیاز باشد، می‌توانید از core یا exchanges import کنید
)
from apps.core.encryption import encrypt_field, decrypt_field # import از core.encryption
from apps.exchanges.exceptions import (
    ExchangeBaseError,
    DataValidationError,
    InvalidSymbolError,
    InvalidAmountError,
    # سایر استثناهای exchanges
)
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد
from apps.instruments.models import Instrument # فرض بر این است که مدل نماد وجود دارد
from apps.exchanges.models import Exchange # فرض بر این است که مدل صرافی وجود دارد

logger = logging.getLogger(__name__)

# --- توابع مربوط به اعتبارسنجی و کار با داده صرافی ---

def validate_exchange_response(response: Dict[str, Any], response_type: str, source_name: str) -> Optional[Dict[str, Any]]:
    """
    Validates the structure and content of an API response from an exchange.
    Applies source-specific validation logic.
    Logs warnings or errors based on the validation results.
    Returns the validated response or None if validation fails critically.
    Raises DataValidationError if structure is invalid.
    """
    try:
        # اعتبارسنجی ساختار کلی (مثلاً وجود فیلدهای خاص)
        if not isinstance(response, dict):
            logger.error(f"Invalid response format from {source_name}: Expected dict, got {type(response)} for {response_type}")
            raise DataValidationError(f"Invalid response format for {response_type} from {source_name}")

        # مثال: اعتبارسنجی پاسخ سفارش (بر اساس فرضیات از ساختار API)
        if response_type == 'ORDER_RESPONSE':
            required_fields = ['orderId', 'symbol', 'side', 'type', 'status', 'price', 'origQty']
            for field in required_fields:
                if field not in response:
                    logger.warning(f"Missing field '{field}' in order response from {source_name}: {response}")
                    # اگر یک فیلد اساسی نبود، ممکن است بخواهید خطایی صادر کنید
                    # if field in ['orderId', 'symbol', 'status']:
                    #     raise DataValidationError(f"Critical field '{field}' missing in order response from {source_name}.")

        # مثال: اعتبارسنجی موجودی (بر اساس فرضیات از ساختار API)
        elif response_type == 'BALANCES':
            if not isinstance(response, list):
                logger.error(f"Invalid balances format from {source_name}: Expected list, got {type(response)}")
                raise DataValidationError("Invalid balances format from {source_name}")
            for balance_item in response:
                if not isinstance(balance_item, dict):
                    logger.error(f"Invalid balance item format from {source_name}: {balance_item}")
                    continue
                required_fields = ['asset', 'free', 'locked'] # مثال برای Binance
                for field in required_fields:
                    if field not in balance_item:
                        logger.warning(f"Missing field '{field}' in balance item from {source_name}: {balance_item}")

        # مثال: اعتبارسنجی اطلاعات حساب (بر اساس فرضیات از ساختار API)
        elif response_type == 'ACCOUNT_INFO':
            # می‌توانید فیلدهای مورد نیاز خاص خود را بررسی کنید
            # e.g., 'canTrade', 'canWithdraw', 'canDeposit', 'accountType', 'balances', ...
            pass

        # مثال: اعتبارسنجی کندل (بر اساس فرضیات از ساختار API)
        elif response_type == 'CANDLE':
            # فرض: response یک لیست است، [open_time, open, high, low, close, volume, ...]
            if not isinstance(response, list) or len(response) < 6:
                logger.error(f"Invalid candle format from {source_name}: Expected list with at least 6 elements, got {type(response)} with {len(response)} elements.")
                raise DataValidationError("Invalid candle format from {source_name}")
            # چک کردن نوع اعداد
            try:
                open_time = int(response[0])
                open_price = Decimal(str(response[1]))
                high_price = Decimal(str(response[2]))
                low_price = Decimal(str(response[3]))
                close_price = Decimal(str(response[4]))
                volume = Decimal(str(response[5]))
            except (ValueError, TypeError, InvalidOperation) as e:
                logger.error(f"Invalid numeric data in candle response from {source_name}: {response}, Error: {e}")
                raise DataValidationError("Invalid numeric data in candle response from {source_name}.")

        # --- اضافه شدن منطق نرمالایز و اعتبارسنجی برای Nobitex و LBank ---
        # مثال: اعتبارسنجی نام‌های متفاوت فیلدها برای Nobitex
        if source_name.upper() == 'NOBITEX':
            if response_type == 'BALANCES':
                # فرض: ساختار فیلدهای Nobitex متفاوت است
                # مثلاً {'BTC': {'balance': '1.5', 'locked': '0.5'}, ...}
                if not isinstance(response, dict):
                    logger.error(f"Invalid balances format from {source_name}: Expected dict, got {type(response)}")
                    raise DataValidationError("Invalid balances format from {source_name}")
                # اعتبارسنجی فیلدهای داخلی
                for asset_data in response.values():
                    if not isinstance(asset_data, dict):
                        continue
                    if 'balance' not in asset_data or 'locked' not in asset_data:
                        logger.warning(f"Missing 'balance' or 'locked' in asset data from {source_name}: {asset_data}")

        # مثال: اعتبارسنجی ساختار سفارش برای LBank
        if source_name.upper() == 'LBANK':
             if response_type == 'ORDER_RESPONSE':
                 # فرض: ساختار فیلدهای LBank متفاوت است
                 # مثلاً {'result': 'success', 'data': {'order_id': '...'}, 'error_code': 0}
                 if not isinstance(response, dict):
                     logger.error(f"Invalid response format from {source_name}: Expected dict.")
                     raise DataValidationError("Invalid response format from {source_name}")
                 if response.get('result') != 'success':
                     logger.error(f"Order response from {source_name} indicates failure: {response}")
                     raise DataValidationError(f"Order placement failed on {source_name}: {response.get('error_msg', 'Unknown error')}")

        # اگر همه چیز معتبر بود، داده را برگردان
        return response

    except DataValidationError as e:
        # این استثنا قبلاً ایجاد شده، فقط دوباره آن را بالا می‌آوریم
        raise
    except Exception as e:
        logger.error(f"Unexpected error during response validation from {source_name} for {response_type}: {str(e)}. Raw  {response}")
        raise DataValidationError(f"Unexpected error during response validation from {source_name} for {response_type}: {str(e)}")


def normalize_data_from_source(raw_ Dict[str, Any], source_name: str, data_type: str) -> Optional[Dict[str, Any]]:
    """
    Normalizes raw data from different exchange sources into a standard format.
    This function maps source-specific field names and structures to a common structure based on the data type.
    """
    try:
        normalized = {}
        source_upper = source_name.upper()

        if data_type == 'OHLCV':
            if source_upper == 'BINANCE':
                # فرض: raw_data یک لیست یا دیکشنری از یک کندل Binance است
                # مثال: {'open_time': 1234567890000, 'open': '50000.00', ...}
                # یا یک لیست: [1234567890000, '50000.00', ...]
                if isinstance(raw_data, dict):
                    k = raw_data
                    normalized = {
                        'timestamp': k.get('open_time', 0) / 1000 if k.get('open_time') else 0, # تبدیل میلی‌ثانیه
                        'open': Decimal(str(k.get('open', 0))),
                        'high': Decimal(str(k.get('high', 0))),
                        'low': Decimal(str(k.get('low', 0))),
                        'close': Decimal(str(k.get('close', 0))),
                        'volume': Decimal(str(k.get('volume', 0))),
                        'quote_volume': Decimal(str(k.get('quote_asset_volume', 0))),
                        'number_of_trades': int(k.get('number_of_trades', 0)),
                        'taker_buy_base_asset_volume': Decimal(str(k.get('taker_buy_base_asset_volume', 0))),
                        'taker_buy_quote_asset_volume': Decimal(str(k.get('taker_buy_quote_asset_volume', 0))),
                        'best_bid': Decimal(str(k.get('best_bid', 0))) if k.get('best_bid') else None,
                        'best_ask': Decimal(str(k.get('best_ask', 0))) if k.get('best_ask') else None,
                    }
                elif isinstance(raw_data, list):
                    # مثال: [1234567890000, '50000.00', '50100.00', ...]
                    normalized = {
                        'timestamp': raw_data[0] / 1000 if raw_data[0] else 0,
                        'open': Decimal(str(raw_data[1])),
                        'high': Decimal(str(raw_data[2])),
                        'low': Decimal(str(raw_data[3])),
                        'close': Decimal(str(raw_data[4])),
                        'volume': Decimal(str(raw_data[5])),
                        'quote_volume': Decimal(str(raw_data[7])) if len(raw_data) > 7 else Decimal('0'),
                        'number_of_trades': int(raw_data[8]) if len(raw_data) > 8 else 0,
                        'taker_buy_base_asset_volume': Decimal(str(raw_data[9])) if len(raw_data) > 9 else Decimal('0'),
                        'taker_buy_quote_asset_volume': Decimal(str(raw_data[10])) if len(raw_data) > 10 else Decimal('0'),
                        'best_bid': None, # ممکن است در کندل وجود نداشته باشد
                        'best_ask': None,
                    }
                else:
                    logger.error(f"Unexpected raw data format for OHLCV from {source_name}: {type(raw_data)}")
                    return None

            elif source_upper == 'COINBASE':
                # مثال: {'time': '2023-10-27T10:00:00.000Z', 'low': '50000.00', 'high': '50100.00', 'open': '50050.00', 'close': '50080.00', 'volume': '100.5'}
                normalized = {
                    'timestamp': int(float(raw_data['time'])), # تبدیل ISO8601 به epoch
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
            # --- اضافه شدن منطق نرمالایز برای Nobitex و LBank ---
            elif source_upper == 'NOBITEX':
                # فرض: raw_data یک کندل از Nobitex است، مثلاً {'timestamp': 1234567890, 'open': '50000', 'high': '50100', 'low': '49900', 'close': '50050', 'volume': '100'}
                # توجه: Nobitex ممکن است فیلدهایی مانند best_bid/ask را جداگانه بدهد
                normalized = {
                    'timestamp': raw_data.get('timestamp', 0),
                    'open': Decimal(str(raw_data.get('open', 0))),
                    'high': Decimal(str(raw_data.get('high', 0))),
                    'low': Decimal(str(raw_data.get('low', 0))),
                    'close': Decimal(str(raw_data.get('close', 0))),
                    'volume': Decimal(str(raw_data.get('volume', 0))),
                    'quote_volume': Decimal(str(raw_data.get('quote_volume', 0))) if 'quote_volume' in raw_data else None,
                    'number_of_trades': int(raw_data.get('number_of_trades', 0)) if 'number_of_trades' in raw_data else None,
                    'taker_buy_base_asset_volume': Decimal(str(raw_data.get('taker_buy_base_vol', 0))) if 'taker_buy_base_vol' in raw_data else None,
                    'taker_buy_quote_asset_volume': Decimal(str(raw_data.get('taker_buy_quote_vol', 0))) if 'taker_buy_quote_vol' in raw_data else None,
                    'best_bid': Decimal(str(raw_data.get('best_bid', 0))) if 'best_bid' in raw_data else None,
                    'best_ask': Decimal(str(raw_data.get('best_ask', 0))) if 'best_ask' in raw_data else None,
                }
            elif source_upper == 'LBANK':
                # فرض: raw_data یک کندل از LBank است، مثلاً ['1234567890', '50000.00', '50100.00', '49900.00', '50050.00', '100.5', '1000000']
                # [Timestamp, Open, High, Low, Close, Volume, QuoteVolume]
                if isinstance(raw_data, list) and len(raw_data) >= 6:
                    normalized = {
                        'timestamp': int(raw_data[0]),
                        'open': Decimal(str(raw_data[1])),
                        'high': Decimal(str(raw_data[2])),
                        'low': Decimal(str(raw_data[3])),
                        'close': Decimal(str(raw_data[4])),
                        'volume': Decimal(str(raw_data[5])),
                        'quote_volume': Decimal(str(raw_data[6])) if len(raw_data) > 6 else None,
                        'number_of_trades': None, # LBank ممکن است این را جداگانه ندهد
                        'taker_buy_base_asset_volume': None,
                        'taker_buy_quote_asset_volume': None,
                        'best_bid': None,
                        'best_ask': None,
                    }
                else:
                    logger.error(f"Invalid candle format received from LBANK: {raw_data}")
                    return None
            # ... سایر صرافی‌ها ...

        elif data_type == 'TICK':
            if source_upper == 'BINANCE':
                # فرض: raw_data شامل فیلدهایی مانند {'p': 'price', 'q': 'qty', 'T': 'time', 'm': 'buyer_market_maker'} است
                normalized = {
                    'timestamp': raw_data['T'] / 1000, # تبدیل میلی‌ثانیه
                    'price': Decimal(raw_data['p']),
                    'quantity': Decimal(raw_data['q']),
                    'side': 'BUY' if raw_data['m'] else 'SELL', # Maker sell = Taker buy
                    'trade_id': raw_data.get('t') # ممکن است وجود نداشته باشد
                }
            elif source_upper == 'NOBITEX':
                 # فرض: raw_data شامل فیلدهایی مانند {'price': '50000', 'volume': '0.1', 'timestamp': 1234567890} است
                 normalized = {
                     'timestamp': raw_data['timestamp'],
                     'price': Decimal(str(raw_data['price'])),
                     'quantity': Decimal(str(raw_data['volume'])),
                     'side': raw_data.get('side', 'UNKNOWN'), # Nobitex ممکن است side را ندهد، باید محاسبه شود
                     'trade_id': raw_data.get('id') # ممکن است فیلد ID وجود داشته باشد
                 }
            elif source_upper == 'LBANK':
                 # فرض: raw_data شامل فیلدهایی مانند {'price': '50000.00', 'amount': '0.1', 'dir': 'up', 'ts': 1234567890} است
                 normalized = {
                     'timestamp': raw_data['ts'],
                     'price': Decimal(str(raw_data['price'])),
                     'quantity': Decimal(str(raw_data['amount'])),
                     'side': 'BUY' if raw_data['dir'] == 'up' else 'SELL',
                     'trade_id': raw_data.get('tid') # ممکن است وجود داشته باشد
                 }
            # ... سایر صرافی‌ها ...

        elif data_type == 'ORDERBOOK':
             if source_upper == 'BINANCE':
                  # فرض: raw_data شامل {'bids': [...], 'asks': [...], 'T': 'time', 'U': 'first_update_id', 'u': 'final_update_id'} است
                  normalized = {
                      'timestamp': raw_data['T'] / 1000, # تبدیل میلی‌ثانیه
                      'bids': [[Decimal(str(bid[0])), Decimal(str(bid[1]))] for bid in raw_data['bids']], # [[Price, Quantity], ...]
                      'asks': [[Decimal(str(ask[0])), Decimal(str(ask[1]))] for ask in raw_data['asks']],
                      'first_update_id': raw_data.get('U'),
                      'final_update_id': raw_data.get('u'),
                      'checksum': raw_data.get('checksum') # ممکن است وجود نداشته باشد
                  }
             elif source_upper == 'NOBITEX':
                  # فرض: raw_data شامل {'bids': [[price, quantity], ...], 'asks': [[price, quantity], ...], 'timestamp': 1234567890} است
                  normalized = {
                      'timestamp': raw_data['timestamp'],
                      'bids': [[Decimal(str(bid[0])), Decimal(str(bid[1]))] for bid in raw_data['bids']],
                      'asks': [[Decimal(str(ask[0])), Decimal(str(ask[1]))] for ask in raw_data['asks']],
                      'first_update_id': None, # Nobitex ممکن است این را ندهد
                      'final_update_id': None,
                      'checksum': None,
                  }
             elif source_upper == 'LBANK':
                  # فرض: raw_data شامل {'data': {'bids': [[price, quantity], ...], 'asks': [[price, quantity], ...]}, 'ts': 1234567890} است
                  orderbook_data = raw_data.get('data', {})
                  normalized = {
                      'timestamp': raw_data['ts'],
                      'bids': [[Decimal(str(bid[0])), Decimal(str(bid[1]))] for bid in orderbook_data.get('bids', [])],
                      'asks': [[Decimal(str(ask[0])), Decimal(str(ask[1]))] for ask in orderbook_data.get('asks', [])],
                      'first_update_id': None,
                      'final_update_id': None,
                      'checksum': None,
                  }
             # ... سایر صرافی‌ها ...

        # --- اضافه شدن منطق نرمالایز برای داده‌های دیگر ---
        # مثلاً برای داده‌های حساب (Account Info)
        elif data_type == 'ACCOUNT_INFO':
            if source_upper == 'BINANCE':
                 # فرض: raw_data شامل {'canTrade': True, 'canWithdraw': True, 'balances': [...]}
                 normalized = {
                     'can_trade': raw_data.get('canTrade', False),
                     'can_withdraw': raw_data.get('canWithdraw', False),
                     'can_deposit': raw_data.get('canDeposit', False),
                     'account_type': raw_data.get('accountType', 'SPOT'),
                     'balances': raw_data.get('balances', []),
                     'permissions': raw_data.get('permissions', []),
                 }
            elif source_upper == 'NOBITEX':
                 # فرض: raw_data شامل {'type': 'spot', 'status': 'active', 'balance': {...}}
                 normalized = {
                     'can_trade': raw_data.get('status') == 'active',
                     'can_withdraw': raw_data.get('can_withdraw', True), # فرض
                     'can_deposit': raw_data.get('can_deposit', True), # فرض
                     'account_type': raw_data.get('type', 'SPOT'),
                     'balances': raw_data.get('balance', {}), # ممکن است ساختار متفاوتی داشته باشد
                     'permissions': [], # Nobitex ممکن است ساختار متفاوتی داشته باشد
                 }
            elif source_upper == 'LBANK':
                 # فرض: raw_data شامل {'result': 'success', 'data': {'type': 'spot', 'status': 'active', 'balance': {...}}}
                 data = raw_data.get('data', {})
                 normalized = {
                     'can_trade': data.get('status') == 'active',
                     'can_withdraw': data.get('can_withdraw', True),
                     'can_deposit': data.get('can_deposit', True),
                     'account_type': data.get('type', 'SPOT'),
                     'balances': data.get('balance', {}),
                     'permissions': [],
                 }
            # ... سایر صرافی‌ها ...

        # اضافه کردن زمان پردازش
        normalized['processed_at'] = timezone.now().isoformat()
        normalized['source'] = source_name

        return normalized

    except (KeyError, ValueError, TypeError, InvalidOperation) as e:
        logger.error(f"Error normalizing data from {source_name} for {data_type}: {str(e)}. Raw  {raw_data}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error during data normalization from {source_name}: {str(e)}. Raw  {raw_data}")
        return None


def validate_ohlcv_data( Dict[str, Any], data_type: str = 'OHLCV') -> Optional[Dict[str, Any]]:
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


def validate_symbol_format(symbol: str) -> bool:
    """
    Checks if a given string is a potentially valid trading symbol format.
    Example: BTCUSDT, ETH/USD, BTC_IRT (for Iranian Toman)
    This function only checks the format, not existence on an exchange.
    """
    # یک الگوی ساده برای نمادها (می‌تواند پیچیده‌تر شود)
    # فقط حروف بزرگ، اعداد، خط فاصله یا اسلش، طول مناسب
    pattern = r'^[A-Z0-9_/\-]{2,32}$'
    return bool(re.match(pattern, symbol))


def is_valid_amount(amount: Any) -> bool:
    """
    Checks if a given value is a valid positive decimal amount.
    """
    try:
        decimal_amount = Decimal(str(amount))
        return decimal_amount > 0
    except (ValueError, TypeError, InvalidOperation):
        return False


def is_valid_price(price: Any) -> bool:
    """
    Checks if a given value is a valid positive decimal price.
    Similar to is_valid_amount but named specifically for prices.
    """
    return is_valid_amount(price)


def is_valid_quantity(quantity: Any) -> bool:
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
    # محاسبه باقیمانده تقسیم قیمت بر اندازه تیک
    remainder = price % tick_size
    # اگر باقیمانده بسیار کوچک باشد (به دلیل دقت)، معتبر فرض می‌شود
    # مثلاً اگر باقیمانده کمتر از 1/1000000 تیک بود، معتبر است
    tolerance = tick_size / Decimal('1000000')
    return remainder < tolerance


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


# --- توابع مربوط به مدیریت IP ---
def validate_ip_list(ip_list_str: str) -> Optional[List[str]]:
    """
    Validates a comma-separated string of IP addresses or CIDR blocks.
    Returns a list of valid IPs/CIDRs or None if invalid format is found.
    Uses core's validation if available.
    """
    # این تابع قبلاً در core.helpers تعریف شد و می‌تواند از آنجا import شود
    # اما اگر نیاز به منطق خاصی در exchanges دارید، می‌توانید آن را بازنویسی کنید
    # برای اینجا، فقط اشاره می‌کنیم که از core.helpers استفاده می‌شود
    # return core_helpers.validate_ip_list(ip_list_str)
    # یا اگر منطق متفاوتی داشتید:
    # if not ip_list_str:
    #     return []
    # try:
    #     ip_list = [item.strip() for item in ip_list_str.split(',')]
    #     validated_ips = []
    #     for ip_str in ip_list:
    #         if not ip_str: # اگر رشته خالی بود، نادیده گرفته شود
    #             continue
    #         if '/' in ip_str: # CIDR block
    #             ip_network(ip_str, strict=False) # Raises ValueError if invalid
    #             validated_ips.append(ip_str)
    #         else: # Single IP
    #             ip_address(ip_str) # Raises ValueError if invalid
    #             validated_ips.append(ip_str)
    #     return validated_ips
    # except ValueError as e:
    #     logger.error(f"Invalid IP/CIDR format in list: {ip_list_str}, Error: {e}")
    #     return None
    # چون تابع در core وجود دارد، فقط import می‌کنیم و استفاده می‌کنیم
    # این تابع در بالای فایل import شده است
    return validate_ip_list_core(ip_list_str) # فرض: نام تابع در core.helpers این است

def is_ip_in_allowed_list(client_ip_str: str, allowed_ips_list: List[str]) -> bool:
    """
    Checks if a client IP is within the list of allowed IPs or CIDR blocks.
    Uses core's validation logic if available.
    """
    # این تابع نیز قبلاً در core.helpers تعریف شد
    # return core_helpers.is_ip_in_allowed_list(client_ip_str, allowed_ips_list)
    # اگر منطق متفاوتی در exchanges وجود داشت، بازنویسی می‌کردیم
    # اما برای اینجا، فرض می‌کنیم از core.helpers استفاده می‌شود
    # این تابع در بالای فایل import شده است
    return is_ip_in_allowed_list_core(client_ip_str, allowed_ips_list) # فرض: نام تابع در core.helpers این است

# --- توابع امنیتی ---
def mask_api_key_or_secret( str) -> str:
    """
    Masks API keys or secrets for logging or display.
    Uses core's mask function if available.
    """
    # استفاده از تابع mask از core
    return mask_sensitive_data_core(data, visible_chars=6) # فرض: نام تابع در core.helpers این است

def hash_data( str) -> str:
    """
    Creates a SHA-256 hash of the input data.
    Useful for hashing sensitive data before logging or storage.
    """
    # استفاده از تابع هش از core یا تعریف مستقیم
    # return core_helpers.hash_data(data) # اگر در core.helpers وجود داشت
    # در اینجا، مستقیماً هش می‌زنیم
    return hashlib.sha256(data.encode()).hexdigest()

def generate_secure_token(length: int = 32) -> str:
    """
    Generates a cryptographically secure random token.
    Suitable for API keys, session IDs, etc.
    """
    # استفاده از تابع از core یا تعریف مستقیم
    # return core_helpers.generate_secure_token(length) # اگر در core.helpers وجود داشت
    # در اینجا، مستقیماً تولید می‌کنیم
    return secrets.token_urlsafe(length)[:length]

# --- توابع مربوط به رمزنگاری ---
def encrypt_api_credentials(api_key: str, api_secret: str) -> tuple[str, str, str]:
    """
    Encrypts API key and secret using core's encryption service.
    Returns (encrypted_key, encrypted_secret, iv).
    """
    # استفاده از تابع رمزنگاری از core
    try:
        from apps.core.encryption import FernetEncryptionService # import از core
        service = FernetEncryptionService()
        enc_key, iv = service.encrypt_field(api_key)
        enc_secret, _ = service.encrypt_field(api_secret) # IV ممکن است یکی برای جفت کلید/مخفی باشد
        return enc_key, enc_secret, iv
    except ImportError as e:
        logger.error(f"Encryption service not available: {e}")
        # ممکن است نیاز باشد یک روش پشتیبان یا خطایی صادر کنید
        raise CoreSystemException("Encryption service is not configured properly.")

def decrypt_api_credentials(encrypted_key: str, encrypted_secret: str, iv: str) -> tuple[str, str]:
    """
    Decrypts API key and secret using core's encryption service.
    Requires the IV used for encryption.
    """
    # استفاده از تابع رمزگشایی از core
    try:
        from apps.core.encryption import FernetEncryptionService
        service = FernetEncryptionService()
        dec_key = service.decrypt_field(encrypted_key, iv)
        dec_secret = service.decrypt_field(encrypted_secret, iv)
        return dec_key, dec_secret
    except ImportError as e:
        logger.error(f"Encryption service not available: {e}")
        raise CoreSystemException("Encryption service is not configured properly.")

# --- توابع مربوط به کار با JSON ---
def safe_json_loads(json_str: str, default: Any = None) -> Any:
    """
    Safely loads a JSON string, returning a default value if it fails.
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError):
        logger.warning(f"Failed to decode JSON string: {json_str[:50]}...") # فقط اولین 50 کاراکتر را نشان می‌دهد
        return default

def safe_json_dumps(obj: Any, default: Any = None) -> str:
    """
    Safely dumps an object to a JSON string, returning a default value if it fails.
    """
    try:
        return json.dumps(obj)
    except (TypeError, ValueError):
        logger.warning(f"Failed to encode object to JSON: {obj}")
        return default or '{}'

# --- توابع مربوط به دقت اعشاری ---
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

# --- توابع کمکی عمومی ---
def get_client_ip(request) -> str:
    """
    Extracts the real client IP, considering proxies (e.g., X-Forwarded-For).
    This function is identical to the one in core.helpers and could be imported from there.
    """
    # این تابع ممکن است در core.helpers نیز وجود داشته باشد و از آنجا import شود
    # return core_helpers.get_client_ip(request) # اگر در core.helpers وجود داشت
    # اما در اینجا، تعریف می‌کنیم یا import می‌کنیم
    # تابع قبلاً در core/helpers تعریف شد
    # بنابراین، می‌توانیم آن را import کنیم
    # از core.helpers import کردیم در ابتدای فایل
    return get_client_ip_core(request) # فرض: نام تابع در core.helpers این است

def generate_device_fingerprint(request) -> str:
    """
    Generates a simple device fingerprint based on request headers.
    This function is identical to the one in core.helpers and could be imported from there.
    """
    # return core_helpers.generate_device_fingerprint(request)
    # از core.helpers import کردیم
    return generate_device_fingerprint_core(request)

def get_location_from_ip(ip: str) -> str:
    """
    Gets location information from an IP address (placeholder implementation).
    In a real implementation, you would use a GeoIP service.
    """
    # return core_helpers.get_location_from_ip(ip)
    # از core.helpers import کردیم
    return get_location_from_ip_core(ip)

# --- توابع مربوط به MAS (اگر نیاز باشد) ---
def generate_agent_trace_id() -> str:
    """
    Generates a unique trace ID for tracking messages/operations across agents in the MAS.
    """
    return str(uuid.uuid4())

def log_agent_interaction(interaction_type: str, source_agent_id: str, target_agent_id: str, details: dict):
    """
    Logs an interaction between agents for monitoring and debugging.
    """
    # این می‌تواند یک ورودی در مدلی مانند AuditLog یا یک مدل جدید MASLog باشد
    from apps.core.models import AuditLog
    AuditLog.objects.create(
        user=None, # عامل، نه کاربر واقعی
        action=f"AGENT_{interaction_type.upper()}",
        target_model="AgentInteraction",
        target_id=target_agent_id,
        details=details,
        ip_address='N/A', # عامل ممکن است IP مشخصی نداشته باشد
        user_agent="MAS_Agent",
    )
    logger.info(f"MAS Interaction: {interaction_type} from {source_agent_id} to {target_agent_id}.")

logger.info("Exchanges helpers loaded successfully.")
