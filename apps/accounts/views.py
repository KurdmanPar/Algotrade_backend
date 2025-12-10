# apps/accounts/views.py

from __future__ import annotations
from typing import Any, Dict
import uuid
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.password_validation import validate_password

from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView, TokenVerifyView
from django.utils import timezone
from django.contrib.auth import login, logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import get_user_model
from django.db import transaction
from django.conf import settings
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes
from django.utils.translation import gettext_lazy as _
import logging

from celery import shared_task, current_app # اضافه شده برای تعریف تاسک‌های Celery
# --- واردات فایل‌های جدید ---
from .models import (
    CustomUser, UserProfile, UserSession, UserAPIKey
)
from .serializers import (
    UserSerializer, RegistrationSerializer, LoginSerializer, ChangePasswordSerializer,
    UserProfileSerializer, UserSessionSerializer, UserAPIKeySerializer
)
from . import permissions as custom_permissions # تغییر نام برای جلوگیری از تداخل
from . import exceptions as custom_exceptions # تغییر نام برای جلوگیری از تداخل
from . import helpers # تغییر نام برای جلوگیری از تداخل
from . import services # تغییر نام برای جلوگیری از تداخل
# ----------------------------

# Set up logger for error tracking
logger = logging.getLogger(__name__)


# -------------------
# API Views
# -------------------

class RegistrationView(generics.CreateAPIView):
    """
    Enhanced user registration with email verification.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = RegistrationSerializer # مشخص کردن سریالایزر برای ساختار بهتر

    def perform_create(self, serializer: RegistrationSerializer) -> CustomUser:
        user = serializer.save()
        # Generate email verification token
        token = default_token_generator.make_token(user)

        # Send verification email asynchronously via Celery task
        send_verification_email_task.delay(user.id, token)

        # Generate tokens for the new user
        refresh = RefreshToken.for_user(user)
        self.refresh_token = refresh # ذخیره برای استفاده در post_save
        return user

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)

        return Response({
            'user': UserSerializer(user).data,
            'message': _("Registration successful. Please check your email for verification."),
            'refresh': str(self.refresh_token),
            'access': str(self.refresh_token.access_token),
            'requires_email_verification': True
        }, status=status.HTTP_201_CREATED)


class LoginView(generics.GenericAPIView):
    """
    Enhanced login with session management and device tracking.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = LoginSerializer

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        # Generate tokens
        refresh = RefreshToken.for_user(user)

        # Update last login information using service
        services.AccountService.update_user_login_info(user, request)

        # Create or update session using service
        services.AccountService.create_or_update_session(user, request)

        return Response({
            'user': UserSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'session_key': request.session.session_key or 'no-session-key',
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    """
    Enhanced logout with session cleanup.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()

            # Deactivate user session using service
            session_key = getattr(request, 'session', {}).get('session_key')
            if session_key:
                services.AccountService.deactivate_session(request.user, session_key)

            logout(request)

            return Response({"message": "Successfully logged out"}, status=status.HTTP_205_RESET_CONTENT)
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            return Response({"error": "Logout failed"}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    Enhanced profile management with partial updates.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self) -> CustomUser:
        return self.request.user

    def patch(self, request, *args: Any, **kwargs: Any) -> Response:
        user = self.get_object()

        # Update user fields
        user_serializer = UserSerializer(
            user,
            data=request.data,
            partial=True
        )
        user_serializer.is_valid(raise_exception=True)
        user_serializer.save()

        # Update profile fields if provided using service
        profile_data = request.data.get('profile', {})
        if profile_data:
            updated_profile = services.AccountService.update_user_profile(user, profile_data)
            # Re-serialize the updated profile if needed
            profile_serializer = UserProfileSerializer(updated_profile)

        return Response(UserSerializer(user).data)


class UserSessionsView(generics.ListAPIView):
    """
    View for managing user sessions with device information.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSessionSerializer

    def get_queryset(self):
        return UserSession.objects.filter(
            user=self.request.user,
            is_active=True
        ).order_by('-created_at')


class UserSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for managing individual user sessions.
    """
    permission_classes = [custom_permissions.IsOwnerOfUser] # استفاده از اجازه‌نامه سفارشی
    serializer_class = UserSessionSerializer

    def get_object(self):
        session_key = self.kwargs['session_id']
        # استفاده از اجازه‌نامه جدید که چک می‌کند آیا شیء متعلق به کاربر فعلی است
        session = UserSession.objects.get(
            session_key=session_key,
            is_active=True
        )
        # اطمینان از اینکه کاربر مالک جلسه است
        if session.user != self.request.user:
            self.permission_denied(self.request) # یا افزایش یک Exception سفارشی
        return session

    def update(self, request, *args: Any, **kwargs: Any) -> Response:
        session = self.get_object()

        # Only allow updating is_active status
        if 'is_active' in request.data:
            session.is_active = request.data['is_active']
            session.save(update_fields=['is_active'])

        serializer = self.get_serializer(session)
        return Response(serializer.data)

    def delete(self, request, *args: Any, **kwargs: Any) -> Response:
        session = self.get_object()
        session.is_active = False
        session.save(update_fields=['is_active'])
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserAPIKeysView(generics.ListCreateAPIView):
    """
    View for managing user API keys with enhanced security.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserAPIKeySerializer

    def get_queryset(self):
        return UserAPIKey.objects.filter(user=self.request.user).order_by('-created_at')

    def perform_create(self, serializer: UserAPIKeySerializer) -> UserAPIKey:
        # اطمینان از اینکه کلید جدید متعلق به کاربر فعلی است
        serializer.save(user=self.request.user)


class UserAPIKeyDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    View for managing individual user API keys.
    """
    permission_classes = [custom_permissions.IsOwnerOfUser] # استفاده از اجازه‌نامه سفارشی
    serializer_class = UserAPIKeySerializer

    def get_object(self) -> UserAPIKey:
        api_key_id = self.kwargs['api_key_id']
        # استفاده از اجازه‌نامه جدید که چک می‌کند آیا شیء متعلق به کاربر فعلی است
        api_key = UserAPIKey.objects.get(
            id=api_key_id
        )
        # اطمینان از اینکه کاربر مالک کلید API است
        if api_key.user != self.request.user:
            self.permission_denied(self.request) # یا افزایش یک Exception سفارشی
        return api_key

    def update(self, request, *args: Any, **kwargs: Any) -> Response:
        api_key = self.get_object()

        # Validate permissions
        if 'permissions' in request.data:
            serializer = UserAPIKeySerializer(
                api_key,
                data=request.data,
                partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()

        serializer = self.get_serializer(api_key)
        return Response(serializer.data)

    def delete(self, request, *args: Any, **kwargs: Any) -> Response:
        api_key = self.get_object()
        api_key.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PartialProfileView(generics.GenericAPIView):
    """
    View for updating only specific profile fields.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserProfileSerializer # می‌تواند مفید باشد

    def patch(self, request, *args: Any, **kwargs: Any) -> Response:
        user = self.request.user
        profile = user.profile

        # Only allow updating specific fields
        allowed_fields = [
            'first_name', 'last_name', 'display_name', 'phone_number',
            'preferred_base_currency', 'risk_level', 'max_active_trades'
        ]

        update_data = {}
        for field in allowed_fields:
            if field in request.data:
                update_data[field] = request.data[field]

        # استفاده از سرویس برای به‌روزرسانی پروفایل
        updated_profile = services.AccountService.update_user_profile(user, update_data)
        profile_serializer = UserProfileSerializer(updated_profile)

        return Response({
            'message': _("Profile updated successfully"),
            'profile': profile_serializer.data
        })


class PasswordResetRequestView(generics.GenericAPIView):
    """
    View for requesting password reset.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        email = request.data.get('email')

        try:
            user = CustomUser.objects.get(email__iexact=email)
            # Generate reset token
            token = default_token_generator.make_token(user)

            # Send reset email asynchronously via Celery task
            send_password_reset_email_task.delay(user.id, token)

        except CustomUser.DoesNotExist:
            pass # برای جلوگیری از شمارش کاربر، هیچ کاری نمی‌کنیم

        # همیشه پاسخ یکسان برای جلوگیری از شمارش کاربر
        return Response({
            'message': _("If an account with that email exists, a password reset link has been sent.")
        }, status=status.HTTP_200_OK)


class PasswordResetConfirmView(generics.GenericAPIView):
    """
    View for confirming password reset with token validation.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request, uidb64: str, token: str, *args: Any, **kwargs: Any) -> Response:
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = CustomUser.objects.get(pk=uid)

            if default_token_generator.check_token(user, token):  # Fixed order of arguments
                # Set new password
                new_password = CustomUser.objects.make_random_password()
                user.set_password(new_password)
                user.save()

                return Response({
                    'message': _("Password has been reset successfully."),
                    'email': user.email
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': _("Invalid or expired token.")
                }, status=status.HTTP_400_BAD_REQUEST)
        except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
            return Response({
                'error': _("Invalid reset link.")
            }, status=status.HTTP_400_BAD_REQUEST)


# تعریف نما (بهتر است در محل مناسب در فایل قرار گیرد)
class ChangePasswordView(APIView):
    """
    View to allow users to change their password.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # تغییر گذرواژه کاربر فعلی
            request.user.set_password(serializer.validated_data['new_password'])
            request.user.save()

            # اختیاری: جلسات قدیمی را غیرفعال کنید یا ...
            # به‌روزرسانی جلسه برای جلوگیری از خروج فوری
            update_session_auth_hash(request, request.user)

            return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)



class TwoFactorSetupView(generics.GenericAPIView):
    """
    View for setting up two-factor authentication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        profile = user.profile

        return Response({
            'two_factor_enabled': profile.two_factor_enabled,
            'backup_codes': getattr(profile, 'backup_codes', []),
            'can_enable_2fa': not profile.two_factor_enabled
        })

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        profile = user.profile

        if profile.two_factor_enabled:
            return Response({
                'error': _("Two-factor authentication is already enabled.")
            }, status=status.HTTP_400_BAD_REQUEST)

        # Generate backup codes
        backup_codes = [str(uuid.uuid4()).replace('-', '')[:8].upper() for _ in range(10)]

        # Store backup codes temporarily using service
        profile.backup_codes = backup_codes
        profile.save()

        # Send backup codes asynchronously via Celery task
        send_2fa_codes_task.delay(user.id, backup_codes)

        return Response({
            'message': _("Two-factor authentication setup initiated. Check your messages for backup codes."),
            'backup_codes_count': len(backup_codes)
        }, status=status.HTTP_200_OK)


class TwoFactorVerifyView(generics.GenericAPIView):
    """
    View for verifying two-factor authentication codes.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        profile = user.profile

        code = request.data.get('code')

        # استفاده از سرویس برای فعال‌سازی 2FA
        success = services.AccountService.enable_2fa(user, code)
        if success:
            return Response({
                'message': _("Two-factor authentication enabled successfully.")
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': _("Invalid verification code.")
            }, status=status.HTTP_400_BAD_REQUEST)


class TwoFactorDisableView(generics.GenericAPIView):
    """
    View for disabling two-factor authentication.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        user = request.user

        # استفاده از سرویس برای غیرفعال‌سازی 2FA
        success = services.AccountService.disable_2fa(user)
        if success:
            return Response({
                'message': _("Two-factor authentication disabled successfully.")
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': _("Two-factor authentication is not enabled.")
            }, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(generics.GenericAPIView):
    """
    View for verifying email address.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        user = request.user
        profile = user.profile

        # Generate verification token
        token = default_token_generator.make_token(user)

        # Send verification email asynchronously via Celery task
        send_verification_email_task.delay(user.id, token)

        return Response({
            'message': _("Verification email sent. Please check your inbox."),
            'email': user.email
        }, status=status.HTTP_200_OK)


class VerifyKYCView(generics.GenericAPIView):
    """
    View for verifying KYC documents.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args: Any, **kwargs: Any) -> Response:
        user = request.user

        # استفاده از سرویس برای به‌روزرسانی وضعیت KYC
        updated_profile = services.AccountService.update_user_kyc_status(user, submitted=True)

        return Response({
            'message': _("KYC documents submitted for review."),
            'status': 'pending'
        }, status=status.HTTP_200_OK)


class AdminUserListView(generics.ListAPIView):
    """
    View for admin users list.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserSerializer

    def get_queryset(self):
        return CustomUser.objects.all().order_by('-date_joined')


class AdminUserDetailView(generics.RetrieveUpdateAPIView):
    """
    View for admin user detail.
    """
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserSerializer

    def get_object(self) -> CustomUser:
        user_id = self.kwargs['user_id']
        return CustomUser.objects.get(pk=user_id)

# Note: The helper functions for sending emails are replaced by Celery tasks
# and are no longer needed in this file for direct synchronous calls.
# However, the logic remains the same within the tasks.

def get_client_ip(request) -> str:
    """
    Extract the real client IP, considering proxies.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def generate_device_fingerprint(request) -> str:
    """
    Generate a device fingerprint based on request headers.
    """
    # استفاده از تابع کمکی از helpers.py
    return helpers.generate_device_fingerprint(request)
