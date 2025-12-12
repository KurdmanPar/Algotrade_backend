# tests/test_core/test_constants.py

import pytest
from apps.core.constants import (
    ErrorCodes,
    USER_TYPE_CHOICES,
    API_KEY_STATUS_CHOICES,
    AUDIT_ACTION_CHOICES,
    MARKET_DATA_TYPE_CHOICES,
    INDICATOR_TYPE_CHOICES,
    RISK_LEVEL_CHOICES,
    TIMEFRAME_CHOICES,
    ORDER_TYPE_CHOICES,
    ORDER_SIDE_CHOICES,
    ORDER_STATUS_CHOICES,
    AGENT_STATUS_CHOICES,
    AGENT_TYPE_CHOICES,
    DEFAULT_BASE_CURRENCY,
    DEFAULT_RISK_LEVEL,
    DEFAULT_MAX_ACTIVE_TRADES,
    DEFAULT_LEVERAGE,
    MAX_API_KEYS_PER_USER,
    MAX_WATCHLISTS_PER_USER,
    SYSTEM_SETTING_DEFAULTS,
    # ... سایر ثابت‌های شما
)

#pytestmark = pytest.mark.django_db # Constants تست نیازی به پایگاه داده ندارد

class TestErrorCodes:
    """
    Tests for the ErrorCodes class.
    """
    def test_general_error_exists(self):
        assert hasattr(ErrorCodes, 'GENERAL_ERROR')
        assert ErrorCodes.GENERAL_ERROR == "GENERAL_ERROR"

    def test_configuration_error_exists(self):
        assert hasattr(ErrorCodes, 'CONFIGURATION_ERROR')
        assert ErrorCodes.CONFIGURATION_ERROR == "CONFIGURATION_ERROR"

    def test_account_locked_exists(self):
        assert hasattr(ErrorCodes, 'ACCOUNT_LOCKED')
        assert ErrorCodes.ACCOUNT_LOCKED == "ACCOUNT_LOCKED"

    def test_all_error_codes_are_strings(self):
        """
        Ensures all attributes of ErrorCodes are strings.
        """
        for attr_name in dir(ErrorCodes):
            if not attr_name.startswith('_'): # Skip private/internal attributes
                attr_value = getattr(ErrorCodes, attr_name)
                assert isinstance(attr_value, str), f"ErrorCodes.{attr_name} is not a string: {type(attr_value)}"


class TestChoiceConstants:
    """
    Tests for the CHOICE tuple constants used in models.
    """
    def test_user_type_choices_format(self):
        """
        Validates the structure of USER_TYPE_CHOICES.
        Should be a list/tuple of 2-tuples (value, label).
        """
        for choice in USER_TYPE_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message') # برای gettext_lazy

    def test_api_key_status_choices_format(self):
        for choice in API_KEY_STATUS_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_audit_action_choices_format(self):
        for choice in AUDIT_ACTION_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_market_data_type_choices_format(self):
        for choice in MARKET_DATA_TYPE_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_indicator_type_choices_format(self):
        for choice in INDICATOR_TYPE_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_risk_level_choices_format(self):
        for choice in RISK_LEVEL_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_timeframe_choices_format(self):
        for choice in TIMEFRAME_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_order_type_choices_format(self):
        for choice in ORDER_TYPE_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_order_side_choices_format(self):
        for choice in ORDER_SIDE_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_order_status_choices_format(self):
        for choice in ORDER_STATUS_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_agent_status_choices_format(self):
        for choice in AGENT_STATUS_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    def test_agent_type_choices_format(self):
        for choice in AGENT_TYPE_CHOICES:
            assert isinstance(choice, tuple) or isinstance(choice, list)
            assert len(choice) == 2
            value, label = choice
            assert isinstance(value, str)
            assert isinstance(label, str) or hasattr(label, 'message')

    # می‌توانید برای سایر CHOICES نیز تست بنویسید


class TestDefaultConstants:
    """
    Tests for the default value constants.
    """
    def test_default_base_currency_is_string(self):
        assert isinstance(DEFAULT_BASE_CURRENCY, str)
        assert DEFAULT_BASE_CURRENCY == "USD" # یا مقداری که قبلاً تعریف کرده‌اید

    def test_default_risk_level_is_string(self):
        assert isinstance(DEFAULT_RISK_LEVEL, str)
        assert DEFAULT_RISK_LEVEL in [choice[0] for choice in RISK_LEVEL_CHOICES] # اطمینان از اینکه مقدار معتبر است

    def test_default_max_active_trades_is_integer(self):
        assert isinstance(DEFAULT_MAX_ACTIVE_TRADES, int)
        assert DEFAULT_MAX_ACTIVE_TRADES > 0

    def test_default_leverage_is_integer_or_decimal(self):
        # بسته به نوع فیلد در مدل، ممکن است Decimal باشد
        assert isinstance(DEFAULT_LEVERAGE, (int, float, Decimal)) # اگر Decimal استفاده شد
        # یا فقط
        # assert isinstance(DEFAULT_LEVERAGE, (int, float))
        assert DEFAULT_LEVERAGE >= 1

    # می‌توانید تست‌هایی برای سایر مقادیر پیش‌فرض نیز بنویسید


class TestLimitConstants:
    """
    Tests for the system limit constants.
    """
    def test_max_api_keys_per_user_is_positive_integer(self):
        assert isinstance(MAX_API_KEYS_PER_USER, int)
        assert MAX_API_KEYS_PER_USER > 0

    def test_max_watchlists_per_user_is_positive_integer(self):
        assert isinstance(MAX_WATCHLISTS_PER_USER, int)
        assert MAX_WATCHLISTS_PER_USER > 0

    # می‌توانید تست‌هایی برای سایر محدودیت‌ها نیز بنویسید


class TestSystemSettingDefaults:
    """
    Tests for the SYSTEM_SETTING_DEFAULTS dictionary.
    """
    def test_system_setting_defaults_is_dictionary(self):
        assert isinstance(SYSTEM_SETTING_DEFAULTS, dict)

    def test_system_setting_defaults_keys_are_strings(self):
        for key in SYSTEM_SETTING_DEFAULTS.keys():
            assert isinstance(key, str)

    def test_system_setting_defaults_values_are_not_none(self):
        for value in SYSTEM_SETTING_DEFAULTS.values():
            # مقادیر پیش‌فرض معمولاً نباید None باشند
            assert value is not None

    # می‌توانید تست‌هایی برای بررسی مقدار خاص یک کلید نیز بنویسید
    def test_global_rate_limit_default_exists_and_is_positive(self):
        assert 'GLOBAL_RATE_LIMIT_PER_MINUTE' in SYSTEM_SETTING_DEFAULTS
        limit = SYSTEM_SETTING_DEFAULTS['GLOBAL_RATE_LIMIT_PER_MINUTE']
        assert isinstance(limit, int)
        assert limit > 0

logger.info("Core constants tests loaded successfully.")
