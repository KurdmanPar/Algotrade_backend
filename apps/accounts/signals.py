# apps/accounts/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import user_logged_in, user_logged_out
from django.utils import timezone
from django.conf import settings
import logging

from .models import CustomUser, UserProfile, UserSession
# --- واردات فایل‌های جدید ---
from . import helpers
# ----------------------------

logger = logging.getLogger(__name__)

@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a UserProfile when a new CustomUser is created.
    """
    if created:
        try:
            UserProfile.objects.create(user=instance)
            logger.info(f"Profile created automatically for new user: {instance.email}")
        except Exception as e:
            logger.error(f"Failed to create profile for user {instance.email}: {str(e)}")


@receiver(user_logged_in)
def user_logged_in_handler(sender, request, user, **kwargs):
    """
    Update last login information when a user logs in.
    Enhanced with device fingerprinting and geolocation.
    """
    try:
        user.last_login_at = timezone.now()
        user.last_login_ip = helpers.get_client_ip(request) # استفاده از تابع کمکی
        user.save(update_fields=['last_login_at', 'last_login_ip'])
        logger.info(f"Login info updated for user {user.email}.")

        # Create or update session with device information
        session_key = request.session.session_key or 'no-session-key' # اطمینان از وجود session_key
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:512]
        # استفاده از تابع کمکی از helpers.py
        device_fingerprint = helpers.generate_device_fingerprint(request)
        location = helpers.get_location_from_ip(user.last_login_ip) # از IP ذخیره شده استفاده می‌کنیم (اگر تابعی در helpers باشد)

        UserSession.objects.update_or_create(
            user=user,
            session_key=session_key,
            defaults={
                'user_agent': user_agent,
                'device_fingerprint': device_fingerprint,
                'location': location,
                'is_active': True,
                'expires_at': timezone.now() + timezone.timedelta(days=30)
            }
        )
        logger.info(f"Session created/updated for user {user.email} with session key {session_key}.")
    except Exception as e:
        logger.error(f"Error in user_logged_in_handler for user {user.email}: {str(e)}")


@receiver(user_logged_out)
def user_logged_out_handler(sender, request, user, **kwargs):
    """
    Deactivate user session when a user logs out.
    """
    try:
        if hasattr(request, 'session') and request.session.session_key:
            updated_count = UserSession.objects.filter(
                user=user,
                session_key=request.session.session_key,
                is_active=True # فقط جلسات فعال را غیرفعال کن
            ).update(is_active=False)
            if updated_count > 0:
                logger.info(f"Session {request.session.session_key} for user {user.email} deactivated.")
            else:
                logger.warning(f"No active session {request.session.session_key} found for user {user.email} to deactivate.")
        else:
            logger.warning(f"Logout called for user {user.email} without a valid session key in request.")
    except Exception as e:
        logger.error(f"Error in user_logged_out_handler for user {user.email}: {str(e)}")

# توجه: توابع get_client_ip و generate_device_fingerprint اکنون در helpers.py تعریف شده‌اند
# و در اینجا دیگر نیازی به تعریف مجدد آن‌ها نیست، مگر اینکه منطق متفاوتی داشته باشند.
# اگر منطق یکسانی دارند، باید از helpers وارد شوند، همانطور که در user_logged_in_handler انجام شد.
# اگر منطق متفاوتی دارند، باید آن منطق را در helpers اعمال کنید و از آنجا وارد کنید.
# تابع get_location_from_ip نیز می‌تواند در helpers قرار گیرد اگر منطق پیچیده‌تری داشته باشد.