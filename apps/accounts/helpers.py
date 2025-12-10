# apps/accounts/helpers.py (یا utils.py)

import re
from typing import List, Optional
from ipaddress import ip_network, ip_address, IPv4Address, IPv6Address
import logging

logger = logging.getLogger(__name__)

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
    """
    try:
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
        return False # If there's an error, deny access for safety

def generate_secure_token(length: int = 32) -> str:
    """
    Generates a cryptographically secure random token.
    """
    import secrets
    return secrets.token_urlsafe(length)

def hash_data(data: str) -> str:
    """
    Creates a SHA-256 hash of the input data.
    Useful for hashing sensitive data before logging or storage.
    """
    import hashlib
    return hashlib.sha256(data.encode()).hexdigest()

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

# مثال استفاده:
# print(mask_sensitive_data("my_secret_api_key_12345", 5)) # -> my_se...2345
