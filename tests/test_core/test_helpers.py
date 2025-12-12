# tests/test_core/test_helpers.py

import pytest
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address, ip_network, ip_address
from apps.core.helpers import (
    validate_symbol_format,
    is_valid_amount,
    is_valid_price,
    is_valid_quantity,
    validate_tick_size,
    validate_ip_list,
    is_ip_in_allowed_list,
    mask_sensitive_data,
    hash_data,
    generate_secure_token,
    round_to_tick_size,
    get_client_ip,
    generate_device_fingerprint,
    get_location_from_ip,
)
from apps.accounts.factories import CustomUserFactory
from apps.instruments.factories import InstrumentFactory
from django.test import RequestFactory
import hashlib

#pytestmark = pytest.mark.django_db # توابع کمکی معمولاً نیازی به پایگاه داده ندارند


class TestValidationHelpers:
    """
    Tests for validation helper functions in apps.core.helpers.
    """
    def test_validate_symbol_format_valid(self):
        """Test validate_symbol_format with valid symbols."""
        valid_symbols = ["BTCUSDT", "ETH/USD", "XRP-USD", "DOGEUSDC", "AAPL.STOCK"]
        for symbol in valid_symbols:
            assert validate_symbol_format(symbol) is True

    def test_validate_symbol_format_invalid(self):
        """Test validate_symbol_format with invalid symbols."""
        invalid_symbols = ["", "BTC USDT", "BTC$USDT", "123", "A" * 33] # Empty, space, invalid char, too long
        for symbol in invalid_symbols:
            assert validate_symbol_format(symbol) is False

    def test_is_valid_amount_valid(self):
        """Test is_valid_amount with valid amounts."""
        valid_amounts = ["1.5", "100", Decimal("0.00000001"), 50.75]
        for amount in valid_amounts:
            assert is_valid_amount(amount) is True

    def test_is_valid_amount_invalid(self):
        """Test is_valid_amount with invalid amounts."""
        invalid_amounts = ["0", "-5", "abc", "", None]
        for amount in invalid_amounts:
            assert is_valid_amount(amount) is False

    def test_is_valid_price_valid(self):
        """Test is_valid_price with valid prices."""
        valid_prices = ["50000.00", "0.00000001", Decimal("123.456789"), 1000.0]
        for price in valid_prices:
            assert is_valid_price(price) is True

    def test_is_valid_price_invalid(self):
        """Test is_valid_price with invalid prices."""
        invalid_prices = ["0", "-100", "not_a_number", ""]
        for price in invalid_prices:
            assert is_valid_price(price) is False

    def test_is_valid_quantity_valid(self):
        """Test is_valid_quantity with valid quantities."""
        valid_quantities = ["0.1", "1", Decimal("1000.00000001"), 10]
        for qty in valid_quantities:
            assert is_valid_quantity(qty) is True

    def test_is_valid_quantity_invalid(self):
        """Test is_valid_quantity with invalid quantities."""
        invalid_quantities = ["0", "-0.5", "invalid", ""]
        for qty in invalid_quantities:
            assert is_valid_quantity(qty) is False

    def test_validate_tick_size(self):
        """Test validate_tick_size for correct rounding."""
        price = Decimal('123.456')
        tick_size = Decimal('0.01')
        # 123.456 -> 123.46 (round half up)
        assert validate_tick_size(price, tick_size) == Decimal('123.46')

        price2 = Decimal('123.454')
        # 123.454 -> 123.45
        assert validate_tick_size(price2, tick_size) == Decimal('123.45')

        price3 = Decimal('123.45')
        # 123.45 -> 123.45 (correct tick size)
        assert validate_tick_size(price3, tick_size) == Decimal('123.45')

        # Invalid tick size (zero or negative)
        assert validate_tick_size(price, Decimal('0')) is False
        assert validate_tick_size(price, Decimal('-0.01')) is False


class TestIPHelpers:
    """
    Tests for IP-related helper functions.
    """
    def test_validate_ip_list_valid(self):
        """Test validate_ip_list with valid IP/CIDR strings."""
        ip_str = "192.168.1.1, 10.0.0.0/8, 2001:db8::1, 172.16.0.0/12"
        result = validate_ip_list(ip_str)
        assert result == ['192.168.1.1', '10.0.0.0/8', '2001:db8::1', '172.16.0.0/12']

    def test_validate_ip_list_invalid(self):
        """Test validate_ip_list with invalid IP/CIDR strings."""
        ip_str = "192.168.1.1, invalid_ip, 10.0.0.0/33" # CIDR out of range
        result = validate_ip_list(ip_str)
        assert result is None # چون یکی از آیتم‌ها نامعتبر است

    def test_validate_ip_list_empty(self):
        """Test validate_ip_list with empty string."""
        ip_str = ""
        result = validate_ip_list(ip_str)
        assert result == []

    def test_is_ip_in_allowed_list_single_ip(self):
        """Test is_ip_in_allowed_list with a single IP."""
        allowed_list = ["192.168.1.1", "10.0.0.0/8"]
        client_ip = "192.168.1.1"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is True

    def test_is_ip_in_allowed_list_cidr_ipv4(self):
        """Test is_ip_in_allowed_list with an IP in a CIDR block (IPv4)."""
        allowed_list = ["192.168.1.1", "10.0.0.0/8"]
        client_ip = "10.0.1.100"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is True

    def test_is_ip_in_allowed_list_cidr_ipv6(self):
        """Test is_ip_in_allowed_list with an IP in a CIDR block (IPv6)."""
        allowed_list = ["2001:db8::/32"]
        client_ip = "2001:db8::1:2:3"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is True

    def test_is_ip_in_allowed_list_not_found(self):
        """Test is_ip_in_allowed_list with an IP not in the list."""
        allowed_list = ["192.168.1.1", "10.0.0.0/8"]
        client_ip = "1.1.1.1"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is False

    def test_is_ip_in_allowed_list_invalid_ip(self):
        """Test is_ip_in_allowed_list with an invalid IP address."""
        allowed_list = ["192.168.1.1"]
        client_ip = "not_an_ip"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is False

    def test_get_client_ip_from_x_forwarded_for(self):
        """Test get_client_ip when X-Forwarded-For header is present."""
        factory = RequestFactory()
        request = factory.get('/', HTTP_X_FORWARDED_FOR='192.168.1.2, 10.0.0.1')
        ip = get_client_ip(request)
        assert ip == '192.168.1.2' # اولین IP

    def test_get_client_ip_from_remote_addr(self):
        """Test get_client_ip when X-Forwarded-For header is not present."""
        factory = RequestFactory()
        request = factory.get('/', REMOTE_ADDR='192.168.1.100')
        ip = get_client_ip(request)
        assert ip == '192.168.1.100'


class TestSecurityHelpers:
    """
    Tests for security-related helper functions.
    """
    def test_mask_sensitive_data(self):
        """Test mask_sensitive_data function."""
        data = "my_secret_api_key_12345"
        masked = mask_sensitive_data(data, 5)
        assert masked == "my_se...2345"

        # Test with short data
        short_data = "abc"
        masked_short = mask_sensitive_data(short_data, 2)
        assert masked_short == "abc" # Should not mask if too short

        # Test with default visible_chars
        default_masked = mask_sensitive_data("longer_data_string", visible_chars=4)
        assert default_masked == "long...ring"

    def test_hash_data(self):
        """Test hash_data function."""
        data = "sensitive_data_to_hash"
        hashed = hash_data(data)
        expected_hash = hashlib.sha256(data.encode()).hexdigest()
        assert hashed == expected_hash
        assert len(hashed) == 64 # SHA-256 hash length

    def test_generate_secure_token(self):
        """Test generate_secure_token function."""
        token = generate_secure_token(16) # 16 bytes -> 32 hex chars + padding
        assert isinstance(token, str)
        assert len(token) >= 16 # طول خروجی بستگی به تعداد بایت ورودی دارد
        # نمی‌توانیم مقدار خاصی را چک کنیم چون تصادفی است، اما می‌توانیم چک کنیم که خالی نباشد
        assert token != ""

    def test_round_to_tick_size(self):
        """
        Test round_to_tick_size function.
        """
        price = Decimal('123.456')
        tick_size = Decimal('0.01')
        expected = Decimal('123.46') # ROUND_HALF_UP
        assert round_to_tick_size(price, tick_size) == expected

        price2 = Decimal('123.454')
        expected2 = Decimal('123.45')
        assert round_to_tick_size(price2, tick_size) == expected2

        price3 = Decimal('123.45')
        expected3 = Decimal('123.45') # Already on tick boundary
        assert round_to_tick_size(price3, tick_size) == expected3

        # Zero or negative tick_size should raise ValueError (based on previous implementation)
        with pytest.raises(ValueError):
            round_to_tick_size(price, Decimal('0'))
        with pytest.raises(ValueError):
            round_to_tick_size(price, Decimal('-0.01'))


class TestMiscellaneousHelpers:
    """
    Tests for other miscellaneous helper functions.
    """
    def test_generate_device_fingerprint(self):
        """
        Test generate_device_fingerprint function.
        This is a simple test based on the headers provided in the request.
        """
        factory = RequestFactory()
        request = factory.get('/')
        request.META['HTTP_USER_AGENT'] = 'Mozilla/5.0 Test Browser'
        request.META['HTTP_ACCEPT_LANGUAGE'] = 'en-US,en;q=0.9'
        request.META['HTTP_ACCEPT_ENCODING'] = 'gzip, deflate'

        fingerprint = generate_device_fingerprint(request)
        # اطمینان از اینکه یک رشته hash با طول مشخص برمی‌گرداند
        assert isinstance(fingerprint, str)
        assert len(fingerprint) == 32 # MD5 hash length

    def test_get_location_from_ip(self):
        """
        Test get_location_from_ip function.
        This is a placeholder test as the function relies on external services.
        """
        # Test localhost
        loc_local = get_location_from_ip('127.0.0.1')
        assert loc_local == "Localhost"

        # Test internal IP
        loc_internal = get_location_from_ip('192.168.1.100')
        assert loc_internal == "Internal Network"

        # Test a public IP (result will be 'Unknown Location' unless mocked or integrated with a service)
        loc_unknown = get_location_from_ip('8.8.8.8')
        assert loc_unknown == "Unknown Location"

# --- تست توابع کمکی مرتبط با داده ---
class TestDataProcessingHelpers:
    """
    Tests for data processing helper functions.
    """
    def test_normalize_data_from_source(self):
        """
        Test normalize_data_from_source function.
        This requires mocking or providing raw data examples for different sources.
        Example for Binance OHLCV:
        """
        # فرض: تابع normalize_data_from_source در helpers.py وجود دارد
        # raw_binance_kline = [1672531199000, "50000.00", "50100.00", "49900.00", "50050.00", "100.5", ...]
        # normalized = helpers.normalize_data_from_source({'k': raw_binance_kline}, 'BINANCE', 'OHLCV')
        # assert normalized['timestamp'] == 1672531199
        # assert normalized['open'] == Decimal('50000.00')
        # ... سایر فیلدها
        pass # این فقط یک مثال است. تست واقعی نیاز به تابع موجود و داده ورودی واقعی دارد

    def test_validate_ohlcv_data(self):
        """
        Test validate_ohlcv_data function.
        """
        # فرض: تابع validate_ohlcv_data در helpers.py وجود دارد
        # valid_data = {'open': '50000', 'high': '50100', 'low': '49900', 'close': '50050', 'volume': '100', 'timestamp': 1234567890}
        # assert helpers.validate_ohlcv_data(valid_data) == valid_data
        #
        # invalid_data = {'open': '50000', 'high': '49900'} # High < Open
        # assert helpers.validate_ohlcv_data(invalid_data) is None
        pass # این فقط یک مثال است. تست واقعی نیاز به تابع موجود دارد

logger.info("Core helpers tests loaded successfully.")
