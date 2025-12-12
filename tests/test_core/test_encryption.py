# tests/test_core/test_encryption.py

import pytest
from decimal import Decimal
from unittest.mock import patch, MagicMock
from django.conf import settings
from apps.core.encryption import (
    FernetEncryptionService,
    # سایر سرویس‌ها/کلاس‌های رمزنگاری شما
)
from apps.core.exceptions import (
    # سایر استثناهای مرتبط با رمزنگاری
    # SecurityException,
    # ConfigurationError,
)

pytestmark = pytest.mark.django_db

class TestFernetEncryptionService:
    """
    Tests for the FernetEncryptionService class.
    """
    def test_encrypt_field_returns_encrypted_data_and_iv(self):
        """
        Test that encrypt_field returns a tuple of (encrypted_data, iv).
        Note: Fernet doesn't use IVs in the traditional sense, but this service might adapt its return signature.
        """
        service = FernetEncryptionService()
        plaintext = "my_secret_data_12345"

        # اطمینان از وجود کلید رمزنگاری در تنظیمات
        if not getattr(settings, 'ENCRYPTION_KEY', None):
            pytest.skip("ENCRYPTION_KEY not set in settings, skipping encryption test.")

        encrypted_data, iv = service.encrypt_field(plaintext)

        # چک کردن نوع خروجی
        assert isinstance(encrypted_data, str)
        # IV در Fernet معمولاً لازم نیست، پس ممکن است یک رشته خالی یا یک مقدار ثابت باشد
        # assert isinstance(iv, str) # یا bytes بسته به پیاده‌سازی

        # چک کردن اینکه داده رمزنگاری شده با داده اولیه متفاوت است
        assert encrypted_data != plaintext

        # چک کردن اینکه داده رمزنگاری شده یک فرمت معتبر (مثلاً base64) دارد
        import base64
        try:
            base64.b64decode(encrypted_data.encode())
            is_base64 = True
        except Exception:
            is_base64 = False
        assert is_base64, "Encrypted data should be base64 encoded."

    def test_decrypt_field_returns_original_plaintext(self):
        """
        Test that decrypt_field returns the original plaintext when given the correct encrypted data and IV.
        """
        service = FernetEncryptionService()
        plaintext = "another_secret_value_67890"

        if not getattr(settings, 'ENCRYPTION_KEY', None):
            pytest.skip("ENCRYPTION_KEY not set in settings, skipping decryption test.")

        encrypted_data, iv = service.encrypt_field(plaintext)

        decrypted_text = service.decrypt_field(encrypted_data, iv)

        assert decrypted_text == plaintext

    def test_decrypt_field_fails_with_wrong_key(self, mocker):
        """
        Test that decrypt_field raises an exception if the wrong key is used.
        """
        service = FernetEncryptionService()
        plaintext = "secret_to_decrypt"

        if not getattr(settings, 'ENCRYPTION_KEY', None):
            pytest.skip("ENCRYPTION_KEY not set in settings, skipping decryption test.")

        encrypted_data, iv = service.encrypt_field(plaintext)

        # mock کردن cipher_suite با کلید اشتباه
        wrong_key = Fernet.generate_key()
        wrong_cipher = Fernet(wrong_key)
        mock_cipher = mocker.patch('apps.core.encryption.FernetEncryptionService._get_cipher_suite', return_value=wrong_cipher)

        with pytest.raises(Exception): # فرض: Fernet.InvalidToken یا ValueError صادر می‌شود
            service.decrypt_field(encrypted_data, iv)

    def test_encrypt_field_handles_non_string_input(self):
        """
        Test that encrypt_field can handle non-string inputs (e.g., int, float) by converting them to string.
        """
        service = FernetEncryptionService()
        plaintext_int = 12345
        plaintext_float = 12.345

        if not getattr(settings, 'ENCRYPTION_KEY', None):
            pytest.skip("ENCRYPTION_KEY not set in settings, skipping encryption test.")

        encrypted_int, _ = service.encrypt_field(plaintext_int)
        encrypted_float, _ = service.encrypt_field(plaintext_float)

        assert isinstance(encrypted_int, str)
        assert isinstance(encrypted_float, str)

        # چک کردن رمزگشایی
        decrypted_int = service.decrypt_field(encrypted_int, "")
        decrypted_float = service.decrypt_field(encrypted_float, "")
        assert decrypted_int == str(plaintext_int)
        assert decrypted_float == str(plaintext_float)

    def test_get_cipher_suite_singleton(self):
        """
        Test that _get_cipher_suite returns the same instance (singleton pattern).
        """
        service1 = FernetEncryptionService()
        service2 = FernetEncryptionService()

        cipher1 = service1._get_cipher_suite()
        cipher2 = service2._get_cipher_suite()

        assert cipher1 is cipher2

    def test_get_cipher_suite_initializes_correctly(self, mocker):
        """
        Test that _get_cipher_suite initializes the Fernet instance with the correct key from settings.
        """
        expected_key = settings.ENCRYPTION_KEY
        if not expected_key:
            pytest.skip("ENCRYPTION_KEY not set in settings, skipping cipher initialization test.")

        mock_fernet = mocker.patch('apps.core.encryption.Fernet')
        service = FernetEncryptionService()
        cipher = service._get_cipher_suite()

        mock_fernet.assert_called_once_with(expected_key.encode() if isinstance(expected_key, str) else expected_key)
        assert cipher == mock_fernet.return_value

# --- تست سایر سرویس‌ها/توابع رمزنگاری ---
# اگر سرویس‌های دیگری مانند AES یا RSA ایجاد کردید، تست‌های مربوطه را اینجا اضافه کنید
# مثلاً:
# class TestAESEncryptionService:
#     def test_encrypt_field(self):
#         # ...
#     def test_decrypt_field(self):
#         # ...

logger.info("Core encryption tests loaded successfully.")
