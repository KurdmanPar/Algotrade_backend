# apps/core/encryption.py

import os
import logging
from cryptography.fernet import Fernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

logger = logging.getLogger(__name__)

# --- رمزنگاری با استفاده از Fernet (Symmetric Encryption) ---

class FernetEncryptionService:
    """
    Service class for handling symmetric encryption and decryption using Fernet.
    Requires a SECRET_KEY to be set in Django settings.
    """
    _cipher_suite = None

    @classmethod
    def _get_cipher_suite(cls):
        """
        Initializes and returns the Fernet cipher suite.
        Reads the encryption key from Django settings.
        """
        if cls._cipher_suite is None:
            key = getattr(settings, 'ENCRYPTION_KEY', None)
            if not key:
                raise ImproperlyConfigured(
                    "ENCRYPTION_KEY not found in Django settings. "
                    "Generate one using Fernet.generate_key() and add it to settings."
                )
            # کلید باید یک بایت استرینگ باشد
            if isinstance(key, str):
                 key = key.encode()
            cls._cipher_suite = Fernet(key)
        return cls._cipher_suite

    @classmethod
    def encrypt_field(cls, plaintext: str) -> tuple[str, str]: # IV برای Fernet نیاز نیست
        """
        Encrypts a plaintext string.
        Returns the encrypted data (as string) and an empty IV string (for compatibility with AES-like schemes).
        """
        try:
            cipher_suite = cls._get_cipher_suite()
            encrypted_bytes = cipher_suite.encrypt(plaintext.encode())
            # Fernet خودش salt یا nonce را مدیریت می‌کند، بنابراین IV اینجا معنی ندارد
            return encrypted_bytes.decode(), "" # IV خالی برگردانده می‌شود
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise # یا مدیریت خطا مناسب

    @classmethod
    def decrypt_field(cls, encrypted_str: str, iv_str: str = "") -> str: # IV نادیده گرفته می‌شود
        """
        Decrypts an encrypted string.
        The IV parameter is kept for compatibility but ignored by Fernet.
        """
        try:
            cipher_suite = cls._get_cipher_suite()
            decrypted_bytes = cipher_suite.decrypt(encrypted_str.encode())
            return decrypted_bytes.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise # یا مدیریت خطا مناسب

# --- رمزنگاری با استفاده از AES (نیازمند cryptography) ---
# این پیچیده‌تر است و نیاز به مدیریت IV دارد.

# from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
# from cryptography.hazmat.primitives import padding
# import secrets
#
# class AESEncryptionService:
#     """
#     Service class for handling AES encryption and decryption.
#     Requires a SECRET_KEY (32 bytes for AES-256) in settings.
#     """
#     @staticmethod
#     def encrypt_field(plaintext: str) -> tuple[str, str]:
#         key = settings.ENCRYPTION_KEY.encode() # یا settings.SECRET_KEY.encode() (اگر 32 بایت باشد)
#         if len(key) != 32:
#             raise ValueError("AES key must be 32 bytes long for AES-256.")
#         iv = secrets.token_bytes(16) # 16 بایت برای AES
#         cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
#         encryptor = cipher.encryptor()
#         padder = padding.PKCS7(128).padder() # 128 بیت (16 بایت) block size for AES
#         padded_data = padder.update(plaintext.encode()) + padder.finalize()
#         ciphertext = encryptor.update(padded_data) + encryptor.finalize()
#         # باید IV و ciphertext را جدا کنیم و کدگذاری کنیم (مثلاً base64)
#         import base64
#         encoded_iv = base64.b64encode(iv).decode('utf-8')
#         encoded_ciphertext = base64.b64encode(ciphertext).decode('utf-8')
#         return encoded_ciphertext, encoded_iv
#
#     @staticmethod
#     def decrypt_field(encrypted_str: str, iv_str: str) -> str:
#         key = settings.ENCRYPTION_KEY.encode() # یا settings.SECRET_KEY.encode()
#         if len(key) != 32:
#             raise ValueError("AES key must be 32 bytes long for AES-256.")
#         import base64
#         iv = base64.b64decode(iv_str.encode('utf-8'))
#         ciphertext = base64.b64decode(encrypted_str.encode('utf-8'))
#         cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
#         decryptor = cipher.decryptor()
#         padded_plaintext = decryptor.update(ciphertext) + decryptor.finalize()
#         unpadder = padding.PKCS7(128).unpadder()
#         plaintext_bytes = unpadder.update(padded_plaintext) + unpadder.finalize()
#         return plaintext_bytes.decode('utf-8')

# --- استفاده ---
# برای مثال، در مدل یا سرویس:
# encrypted_value, iv = FernetEncryptionService.encrypt_field("my_secret_value")
# decrypted_value = FernetEncryptionService.decrypt_field(encrypted_value, iv)

logger.info("Encryption service components loaded.")
