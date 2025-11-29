# apps/accounts/signals.py
from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.dispatch import receiver
from apps.logging_app.models import SystemLog

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    SystemLog.objects.create(
        level='INFO',
        source='Auth',
        message=f'User {user.email} logged in successfully.',
        user=user,
        context={'ip': request.META.get('REMOTE_ADDR')}
    )

@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    SystemLog.objects.create(
        level='WARNING',
        source='Auth',
        message=f'Login failed for email: {credentials.get("email")}',
        context={'ip': request.META.get('REMOTE_ADDR')}
    )