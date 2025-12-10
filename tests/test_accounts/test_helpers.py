# tests/test_accounts/test_helpers.py

import pytest
from apps.accounts.helpers import (
    validate_ip_list,
    is_ip_in_allowed_list,
    generate_secure_token,
    hash_data,
    mask_sensitive_data,
)

pytestmark = pytest.mark.django_db # Not strictly needed for helpers, but included for consistency

class TestAccountHelpers:
    """
    Test suite for the helper functions in accounts app.
    """

    def test_validate_ip_list_valid(self):
        """Test validate_ip_list with valid IPs and CIDRs."""
        ip_str = "192.168.1.1, 10.0.0.0/8, 2001:db8::1"
        result = validate_ip_list(ip_str)
        assert result == ['192.168.1.1', '10.0.0.0/8', '2001:db8::1']

    def test_validate_ip_list_invalid(self):
        """Test validate_ip_list with invalid IPs."""
        ip_str = "invalid_ip, 10.0.0.0/8"
        result = validate_ip_list(ip_str)
        assert result is None

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

    def test_is_ip_in_allowed_list_cidr(self):
        """Test is_ip_in_allowed_list with an IP in a CIDR block."""
        allowed_list = ["192.168.1.1", "10.0.0.0/8"]
        client_ip = "10.0.1.100"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is True

    def test_is_ip_in_allowed_list_not_found(self):
        """Test is_ip_in_allowed_list with an IP not in the list."""
        allowed_list = ["192.168.1.1", "10.0.0.0/8"]
        client_ip = "1.1.1.1"
        assert is_ip_in_allowed_list(client_ip, allowed_list) is False

    def test_generate_secure_token(self):
        """Test generate_secure_token generates a string."""
        token = generate_secure_token(16) # 16 bytes -> 32 hex chars + padding
        assert isinstance(token, str)
        assert len(token) > 0

    def test_hash_data(self):
        """Test hash_data creates a SHA-256 hash."""
        data = "sensitive_data"
        hashed = hash_data(data)
        assert isinstance(hashed, str)
        assert len(hashed) == 64 # SHA-256 produces 64 hex characters

    def test_mask_sensitive_data(self):
        """Test mask_sensitive_data masks data correctly."""
        data = "my_api_key_12345"
        masked = mask_sensitive_data(data, 5)
        assert masked == "my_ap..._12345"

        # Test with short data
        short_data = "abc"
        masked_short = mask_sensitive_data(short_data, 2)
        assert masked_short == "abc" # Should not mask if too short
