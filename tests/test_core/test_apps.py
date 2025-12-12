# tests/test_core/test_apps.py

import pytest
from django.apps import apps
from django.test import override_settings
from apps.core.apps import CoreConfig
from apps.core.models import AuditLog, SystemSetting, CacheEntry # فرض بر این است که مدل‌هایی وجود دارند
import logging

pytestmark = pytest.mark.django_db

class TestCoreAppConfig:
    """
    Tests for the CoreConfig class in apps.py.
    """

    @pytest.fixture
    def core_config(self):
        """
        Fixture to get the CoreConfig instance.
        """
        return apps.get_app_config('core')

    def test_core_app_config_name(self, core_config):
        """
        Test that the app config name is correctly set.
        """
        assert core_config.name == 'apps.core'

    def test_core_app_config_verbose_name(self, core_config):
        """
        Test that the app config verbose name is correctly set.
        """
        assert core_config.verbose_name == 'Core System'

    def test_core_app_config_default_auto_field(self, core_config):
        """
        Test that the default_auto_field is correctly set.
        """
        assert core_config.default_auto_field == 'django.db.models.BigAutoField'

    def test_core_app_config_ready_method_loads_signals(self, mocker, caplog):
        """
        Test that the ready() method correctly imports and registers signals.
        Uses caplog to capture log messages.
        """
        # Mock کردن ایمپورت apps.core.signals
        mock_import = mocker.patch('apps.core.apps.import_module')

        # اجرای متد ready
        with caplog.at_level(logging.INFO):
            core_config = CoreConfig('apps.core', None) # module=None برای سادگی
            core_config.ready()

        # چک کردن اینکه آیا فایل signals واقعاً import شده است
        mock_import.assert_called_once_with('apps.core.signals')

        # چک کردن اینکه آیا پیام لاگ مربوطه چاپ شده است
        assert "Signals for 'core' app loaded successfully." in caplog.text


    # --- تست مدل‌هایی که در ready() ممکن است مورد استفاده قرار گیرند ---
    def test_models_accessible_after_ready(self, core_config):
        """
        Test that models defined in core are accessible after the app is loaded.
        """
        # متد ready() قبلاً اجرا شده است (هنگام شروع پروژه)
        # پس فقط چک می‌کنیم که آیا مدل‌ها وجود دارند
        assert apps.get_model('core', 'AuditLog') == AuditLog
        assert apps.get_model('core', 'SystemSetting') == SystemSetting
        assert apps.get_model('core', 'CacheEntry') == CacheEntry
        # ... سایر مدل‌ها ...

    # --- تست تنظیمات مربوط به core در ready() (اگر وجود داشت) ---
    # مثال: اگر در ready() تنظیماتی برای کش یا لاگ اعمال می‌شد
    # def test_core_settings_loaded_in_ready(self, mocker):
    #     mock_setting = mocker.patch('apps.core.apps.settings.CORE_SPECIFIC_SETTING')
    #     mock_setting.return_value = 'expected_value'
    #     core_config = CoreConfig('apps.core', None)
    #     core_config.ready()
    #     # چک کنید که تنظیمات مورد نظر در ready قرار گرفته یا اعمال شده باشند
    #     # این بستگی به منطق داخل ready() دارد
    #     assert settings.CORE_SPECIFIC_SETTING == 'expected_value' # اگر در ready تغییر کرد

# --- تست سایر منطق‌های ready (اگر وجود داشت) ---
# مثلاً اگر در ready() یک کار خاص انجام می‌دادید یا یک اکشن ادمین ثبت می‌کردید
# class TestCoreAppReadyLogic:
#     def test_custom_startup_logic(self, mocker):
#         mock_custom_func = mocker.patch('apps.core.apps.some_custom_startup_function')
#         core_config = CoreConfig('apps.core', None)
#         core_config.ready()
#         mock_custom_func.assert_called_once()

logger.info("Core app config tests loaded successfully.")
