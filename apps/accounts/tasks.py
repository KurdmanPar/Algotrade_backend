# apps/accounts/tasks.py

from celery import shared_task
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.contrib.auth import get_user_model
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.utils import timezone # اضافه شده برای استفاده در تاسک‌های تمیزکاری
import logging

from .models import UserSession, UserAPIKey
from .services import AccountService # فرض می‌کنیم AccountService شامل منطق‌های کمکی است
# --- واردات فایل‌های جدید ---
from . import exceptions as custom_exceptions # تغییر نام برای جلوگیری از تداخل
from . import helpers # تغییر نام برای جلوگیری از تداخل
# ----------------------------

logger = logging.getLogger(__name__)
User = get_user_model()

@shared_task
def send_verification_email_task(user_id: int, token: str) -> None:
    """
    Celery task for sending email verification asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        verification_url = f"{settings.FRONTEND_URL}/verify-email/{uid}/{token}/"

        subject = _("Verify your email address")
        context = {
            'user': user,
            'verification_url': verification_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Algorithmic Trading System'),
        }

        text_content = render_to_string('accounts/verification_email.txt', context)
        html_content = render_to_string('accounts/verification_email.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Verification email task completed for user {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for verification email task.")
    except Exception as e:
        logger.error(f"Failed to send verification email task for user id {user_id}: {str(e)}")
        # می‌توانید بر اساس نیاز، دوباره تلاش کنید یا خطایی را گزارش دهید

@shared_task
def send_password_reset_email_task(user_id: int, token: str) -> None:
    """
    Celery task for sending password reset email asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_url = f"{settings.FRONTEND_URL}/reset-password/{uid}/{token}/"

        subject = _("Reset your password")
        context = {
            'user': user,
            'reset_url': reset_url,
            'site_name': getattr(settings, 'SITE_NAME', 'Algorithmic Trading System'),
        }

        text_content = render_to_string('accounts/password_reset_email.txt', context)
        html_content = render_to_string('accounts/password_reset_email.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Password reset email task completed for user {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for password reset email task.")
    except Exception as e:
        logger.error(f"Failed to send password reset email task for user id {user_id}: {str(e)}")

@shared_task
def send_2fa_codes_task(user_id: int, codes: list[str]) -> None:
    """
    Celery task for sending 2FA backup codes asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        subject = _("Your Two-Factor Authentication Backup Codes")

        context = {
            'user': user,
            'codes': codes,
            'site_name': getattr(settings, 'SITE_NAME', 'Algorithmic Trading System'),
            'expiration_time': "10 minutes",
        }

        text_content = render_to_string('accounts/two_factor_backup_codes.txt', context)
        html_content = render_to_string('accounts/two_factor_backup_codes.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"2FA backup codes task completed for user {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {user_id} does not exist for 2FA codes task.")
    except Exception as e:
        logger.error(f"Failed to send 2FA backup codes task for user id {user_id}: {str(e)}")

@shared_task
def deactivate_user_session_task(user_id: int, session_key: str) -> None:
    """
    Celery task for deactivating a user session asynchronously.
    Useful for tasks like session cleanup after logout or inactivity.
    """
    try:
        user = User.objects.get(id=user_id)
        success = AccountService.deactivate_session(user, session_key)
        if success:
            logger.info(f"Session {helpers.mask_sensitive_data(session_key)} deactivated for user {user.email} via task.")
        else:
            logger.warning(f"Session {helpers.mask_sensitive_data(session_key)} for user {user.email} was not found or already inactive.")
    except User.DoesNotExist:
        logger.error(f"User with id {helpers.mask_sensitive_data(str(user_id))} does not exist for session deactivation task.")
    except Exception as e:
        logger.error(f"Failed to deactivate session {helpers.mask_sensitive_data(session_key)} for user id {helpers.mask_sensitive_data(str(user_id))}: {str(e)}")

@shared_task
def revoke_api_key_task(user_id: int, api_key_id: str) -> None:
    """
    Celery task for revoking (deleting) a user's API key asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        success = AccountService.revoke_api_key(user, api_key_id)
        if success:
            logger.info(f"API key {helpers.mask_sensitive_data(api_key_id)} revoked for user {user.email} via task.")
        else:
            logger.warning(f"API key {helpers.mask_sensitive_data(api_key_id)} for user {user.email} was not found.")
    except User.DoesNotExist:
        logger.error(f"User with id {helpers.mask_sensitive_data(str(user_id))} does not exist for API key revocation task.")
    except custom_exceptions.InvalidAPIKeyError as e: # نمونه استفاده از Exception سفارشی
        logger.error(f"Custom InvalidAPIKeyError during revocation of {helpers.mask_sensitive_data(api_key_id)} for user {helpers.mask_sensitive_data(str(user_id))}: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to revoke API key {helpers.mask_sensitive_data(api_key_id)} for user id {helpers.mask_sensitive_data(str(user_id))}: {str(e)}")

@shared_task
def cleanup_expired_sessions_task() -> None:
    """
    Celery task for periodically cleaning up expired user sessions.
    This should be scheduled using Celery Beat.
    """
    try:
        expired_sessions_count = UserSession.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        ).update(is_active=False)
        logger.info(f"{expired_sessions_count} expired sessions deactivated by cleanup task.")
    except Exception as e:
        logger.error(f"Failed to cleanup expired sessions: {str(e)}")

@shared_task
def cleanup_expired_api_keys_task() -> None:
    """
    Celery task for periodically cleaning up expired API keys.
    This should be scheduled using Celery Beat if expiration is implemented for API keys.
    """
    try:
        # فرض کنید مدل UserAPIKey دارای فیلد expires_at است
        expired_keys_count = UserAPIKey.objects.filter(
            expires_at__lt=timezone.now(),
            is_active=True
        ).update(is_active=False)
        logger.info(f"{expired_keys_count} expired API keys deactivated by cleanup task.")
    except Exception as e:
        logger.error(f"Failed to cleanup expired API keys: {str(e)}")

# توجه: این تاسک‌ها فقط مثال‌هایی از کاربردهای ممکن تاسک‌های آسنکرون در اپلیکیشن accounts هستند.
# بسته به نیازهای خاص سیستم، تاسک‌های دیگری ممکن است اضافه شوند.
# مثلاً تاسکی برای ارسال ایمیل هشدار به کاربر در صورت فعالیت مشکوک.
@shared_task
def send_security_alert_task(user_id: int, alert_message: str) -> None:
    """
    Celery task for sending security alerts to a user asynchronously.
    """
    try:
        user = User.objects.get(id=user_id)
        subject = _("Security Alert")
        context = {
            'user': user,
            'alert_message': alert_message,
            'site_name': getattr(settings, 'SITE_NAME', 'Algorithmic Trading System'),
        }

        text_content = render_to_string('accounts/security_alert.txt', context)
        html_content = render_to_string('accounts/security_alert.html', context)

        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()

        logger.info(f"Security alert sent to user {user.email}")
    except User.DoesNotExist:
        logger.error(f"User with id {helpers.mask_sensitive_data(str(user_id))} does not exist for security alert task.")
    except Exception as e:
        logger.error(f"Failed to send security alert to user id {helpers.mask_sensitive_data(str(user_id))}: {str(e)}")
