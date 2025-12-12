# tests/test_core/test_apps.py

import pytest
from django.apps import apps
from django.test import override_settings
from apps.core.apps import CoreConfig
import logging

logger = logging.getLogger(__name__)

#pytestmark = pytest.mark.django_db # Apps config تست نیازی به پایگاه داده ندارد

class TestCoreAppsConfig:
    """
    Tests for the CoreConfig class in apps/core/apps.py.
    """

    def test_core_config_name(self):
        """
        Test that the name of the app config is correctly set.
        """
        config = CoreConfig
        assert config.name == 'apps.core'

    def test_core_config_verbose_name(self):
        """
        Test that the verbose name of the app config is correctly set.
        """
        config = CoreConfig
        # توجه: verbose_name یک ویژگی کلاس نیست، بلکه در متا مدل است
        # برای چک کردن verbose_name، باید نمونه‌ای از کلاس ایجاد کنیم
        instance = CoreConfig('apps.core', apps.get_app_config('core').module)
        # این کار نیازمند این است که app_label در apps.py یا Meta مدل تعریف شده باشد
        # یا اینکه از apps.get_app_config استفاده کنیم
        app_config = apps.get_app_config('core')
        assert app_config.verbose_name == "Core System" # بسته به مقداری که در apps.py تنظیم شده است

    def test_core_config_default_auto_field(self):
        """
        Test that the default_auto_field is correctly set.
        """
        config = CoreConfig
        assert config.default_auto_field == 'django.db.models.BigAutoField'

    def test_ready_method_registers_signals(self, mocker, caplog):
        """
        Test that the ready method successfully imports and connects signals.
        This test mocks the import_module to avoid actually loading signals during test.
        """
        # Mock کردن import_module
        mock_import = mocker.patch('apps.core.apps.import_module')

        # اجرای متد ready
        with caplog.at_level(logging.INFO):
            config_instance = CoreConfig('apps.core', None) # module=None برای سادگی
            config_instance.ready()

        # چک کردن اینکه آیا import_module با مسیر صحیح فراخوانی شد
        mock_import.assert_called_once_with('apps.core.signals')

        # چک کردن اینکه آیا پیام لاگ مربوطه چاپ شده است
        assert "Signals for 'core' app loaded successfully." in caplog.text

    def test_ready_method_handles_import_error(self, mocker, caplog):
        """
        Test that the ready method gracefully handles an ImportError when loading signals.
        """
        # Mock کردن import_module تا یک ImportError صادر کند
        mocker.patch('apps.core.apps.import_module', side_effect=ImportError("Module not found"))

        # اجرای متد ready
        with caplog.at_level(logging.ERROR):
            config_instance = CoreConfig('apps.core', None)
            config_instance.ready()

        # چک کردن اینکه آیا پیام خطا لاگ شده است
        assert "Failed to load signals for 'core' app" in caplog.text

    # --- تست سایر منطق‌های ready (اگر وجود داشت) ---
    # مثلاً اگر در ready() یک کار خاص انجام می‌دادید یا یک اکشن ادمین ثبت می‌کردید
    # def test_ready_registers_custom_action(self, mocker):
    #     mock_register_action = mocker.patch('apps.core.apps.admin_register_custom_action')
    #     core_config = CoreConfig('apps.core', None)
    #     core_config.ready()
    #     mock_register_action.assert_called_once()

    # def test_ready_loads_settings(self, mocker):
    #     # مثال: چک کردن اینکه آیا تنظیمات سیستمی از پایگاه داده یا کش بارگذاری می‌شود
    #     # این نیازمند پیاده‌سازی خاصی در ready() است
    #     pass # فقط نمونه، اگر چنین منطقی وجود داشت

logger.info("Core app config tests loaded successfully.")
