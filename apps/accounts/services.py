# apps/accounts/services.py

from __future__ import annotations
from typing import Any, Dict, Tuple, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from .models import UserSession, UserProfile, UserAPIKey
from .serializers import UserSerializer, UserProfileSerializer, UserAPIKeySerializer
import logging
import hashlib

# --- واردات فایل‌های جدید ---
from . import exceptions as custom_exceptions
from . import helpers
# ----------------------------

logger = logging.getLogger(__name__)
User = get_user_model()

class AccountService:
    """
    Service class for handling account-related business logic.
    This class encapsulates the logic for user registration, profile updates,
    session management, API key management, etc., promoting separation of concerns.
    """

    @staticmethod
    def create_user_with_profile(validated_data: Dict[str, Any]) -> User:
        """
        Creates a user and their associated profile within a database transaction.
        """
        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    email=validated_data['email'],
                    password=validated_data['password'],
                    first_name=validated_data.get('first_name', ''),
                    last_name=validated_data.get('last_name', ''),
                    username=validated_data.get('username', validated_data['email']) # Example logic
                )
                # Create the associated profile automatically
                UserProfile.objects.create(user=user)
            logger.info(f"User {user.email} created successfully.")
            return user
        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise # Re-raise to be handled by the view

    @staticmethod
    def update_user_profile(user: User, profile_data: Dict[str, Any]) -> UserProfile:
        """
        Updates the user's profile data.
        """
        try:
            profile = user.profile
            # اعتبارسنجی IP آدرس‌ها در allowed_ips قبل از ذخیره
            if 'allowed_ips' in profile_data:
                validated_ips = helpers.validate_ip_list(profile_data['allowed_ips'])
                if validated_ips is not None:
                    profile_data['allowed_ips'] = ','.join(validated_ips)
                else:
                    # اگر اعتبارسنجی شکست خورد، یک استثنا یا پاسخ خطا ایجاد کنید
                    raise ValidationError("Invalid IP address or CIDR format in allowed_ips.")

            profile_serializer = UserProfileSerializer(
                profile,
                data=profile_data,
                partial=True
            )
            profile_serializer.is_valid(raise_exception=True)
            updated_profile = profile_serializer.save()
            logger.info(f"Profile for user {user.email} updated successfully.")
            return updated_profile
        except ValidationError as ve:
            logger.error(f"Validation error updating profile for user {user.email}: {ve}")
            raise # Re-raise for the view to handle
        except Exception as e:
            logger.error(f"Error updating profile for user {user.email}: {str(e)}")
            raise

    @staticmethod
    def create_or_update_session(user: User, request) -> UserSession:
        """
        Creates or updates a user session based on request details.
        """
        try:
            session_key = request.session.session_key or 'no-session-key'
            user_agent = request.META.get('HTTP_USER_AGENT', '')[:512]
            # استفاده از تابع کمکی از helpers.py
            device_fingerprint = helpers.generate_device_fingerprint(request)

            session, created = UserSession.objects.update_or_create(
                user=user,
                session_key=session_key,
                defaults={
                    'user_agent': user_agent,
                    'device_fingerprint': device_fingerprint,
                    'is_active': True,
                    'expires_at': timezone.now() + timezone.timedelta(days=30)
                }
            )
            if created:
                logger.info(f"New session created for user {user.email}.")
            else:
                logger.info(f"Existing session updated for user {user.email}.")
            return session
        except Exception as e:
            logger.error(f"Error creating/updating session for user {user.email}: {str(e)}")
            raise

    @staticmethod
    def deactivate_session(user: User, session_key: str) -> bool:
        """
        Deactivates a specific user session.
        """
        try:
            updated_count = UserSession.objects.filter(
                user=user,
                session_key=session_key,
                is_active=True
            ).update(is_active=False)
            if updated_count > 0:
                logger.info(f"Session {session_key} for user {user.email} deactivated.")
                return True
            else:
                logger.warning(f"No active session {session_key} found for user {user.email} to deactivate.")
                return False
        except Exception as e:
            logger.error(f"Error deactivating session {session_key} for user {user.email}: {str(e)}")
            return False

    @staticmethod
    def update_user_login_info(user: User, request) -> None:
        """
        Updates user's last login time and IP address.
        """
        try:
            user.last_login_at = timezone.now()
            user.last_login_ip = AccountService.get_client_ip(request)
            user.save(update_fields=['last_login_at', 'last_login_ip'])
            logger.info(f"Login info updated for user {user.email}.")
        except Exception as e:
            logger.error(f"Error updating login info for user {user.email}: {str(e)}")
            raise # Or handle as appropriate

    @staticmethod
    def get_client_ip(request) -> str:
        """
        Extracts the real client IP, considering proxies.
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

    @staticmethod
    def create_api_key(user: User, name: str, permissions: list) -> UserAPIKey:
        """
        Creates a new API key for the user.
        """
        try:
            api_key = UserAPIKey.objects.create(
                user=user,
                name=name,
                permissions=permissions
            )
            logger.info(f"API key '{name}' created for user {user.email}.")
            return api_key
        except Exception as e:
            logger.error(f"Error creating API key for user {user.email}: {str(e)}")
            raise

    @staticmethod
    def revoke_api_key(user: User, api_key_id: str) -> bool:
        """
        Revokes (deletes) a specific API key for the user.
        """
        try:
            api_key = UserAPIKey.objects.get(user=user, id=api_key_id)
            api_key.delete()
            logger.info(f"API key {api_key_id} revoked for user {user.email}.")
            return True
        except UserAPIKey.DoesNotExist:
            logger.warning(f"API key {api_key_id} not found for user {user.email}.")
            return False
        except Exception as e:
            logger.error(f"Error revoking API key {api_key_id} for user {user.email}: {str(e)}")
            return False

    @staticmethod
    def verify_api_key(api_key_string: str) -> Tuple[bool, Optional[User], Optional[UserAPIKey]]:
        """
        Verifies an API key string and returns (is_valid, user, api_key_object).
        """
        try:
            # Assuming api_key_string is the key itself (not a hash)
            # In a real scenario, you might hash the provided key and compare to stored hash
            api_key = UserAPIKey.objects.get(key=api_key_string, is_active=True)
            if api_key.is_valid():
                logger.info(f"API key verified for user {api_key.user.email}.")
                return True, api_key.user, api_key
            else:
                logger.info(f"API key expired for user {api_key.user.email}.")
                return False, api_key.user, api_key
        except UserAPIKey.DoesNotExist:
            logger.warning(f"Invalid API key provided.")
            return False, None, None
        except Exception as e:
            logger.error(f"Error verifying API key: {str(e)}")
            return False, None, None

    @staticmethod
    def update_user_kyc_status(user: User, submitted: bool = True) -> UserProfile:
        """
        Updates the KYC submission status for a user.
        """
        try:
            profile = user.profile
            if submitted:
                profile.kyc_submitted_at = timezone.now()
            else:
                profile.kyc_submitted_at = None
            profile.save(update_fields=['kyc_submitted_at'])
            logger.info(f"KYC status updated for user {user.email}.")
            return profile
        except Exception as e:
            logger.error(f"Error updating KYC status for user {user.email}: {str(e)}")
            raise

    @staticmethod
    def enable_2fa(user: User, verified_code: str) -> bool:
        """
        Enables 2FA for a user after verifying the code.
        """
        try:
            profile = user.profile
            if profile.backup_codes and verified_code in profile.backup_codes:
                profile.two_factor_enabled = True
                profile.backup_codes = []
                profile.save(update_fields=['two_factor_enabled', 'backup_codes'])
                logger.info(f"2FA enabled for user {user.email}.")
                return True
            else:
                logger.warning(f"Invalid 2FA verification code for user {user.email}.")
                # می‌توانید یک استثنا سفارشی نیز ایجاد کنید
                # raise custom_exceptions.TwoFactorRequiredError("Invalid 2FA code provided.")
                return False
        except Exception as e:
            logger.error(f"Error enabling 2FA for user {user.email}: {str(e)}")
            raise

    @staticmethod
    def disable_2fa(user: User) -> bool:
        """
        Disables 2FA for a user.
        """
        try:
            profile = user.profile
            if profile.two_factor_enabled:
                profile.two_factor_enabled = False
                profile.backup_codes = [] # Clear any stored codes
                profile.save(update_fields=['two_factor_enabled', 'backup_codes'])
                logger.info(f"2FA disabled for user {user.email}.")
                return True
            else:
                logger.warning(f"2FA not enabled for user {user.email}.")
                return False
        except Exception as e:
            logger.error(f"Error disabling 2FA for user {user.email}: {str(e)}")
            raise

    # --- توابع جدید ممکن ---
    @staticmethod
    def check_user_ip_access(user: User, request_ip: str) -> bool:
        """
        Checks if a given IP address is allowed for the user based on their profile settings.
        """
        try:
            profile = user.profile
            if not profile.allowed_ips:
                # اگر لیست IPها خالی بود، فرض می‌کنیم دسترسی مجاز است
                return True

            allowed_ips_list = profile.allowed_ips.split(',')
            is_allowed = helpers.is_ip_in_allowed_list(request_ip, allowed_ips_list)
            if not is_allowed:
                logger.warning(f"IP {request_ip} is not allowed for user {user.email}.")
            return is_allowed
        except Exception as e:
            logger.error(f"Error checking IP access for user {user.email}: {str(e)}")
            # ممکن است بخواهید در صورت خطا، دسترسی را رد کنید
            return False
