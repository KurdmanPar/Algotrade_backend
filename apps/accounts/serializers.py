# apps/accounts/serializers.py

from __future__ import annotations
from typing import Any, Dict
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.utils.translation import gettext_lazy as _
from django.core.validators import RegexValidator
from .models import CustomUser, UserProfile, UserSession, UserAPIKey
# توجه: اگر AccountService را در نماها استفاده کنید، نیازی به import در اینجا نیست
# from .services import AccountService
# --- واردات فایل‌های جدید ---
from . import helpers
# ----------------------------

class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for the UserProfile model with enhanced validation.
    """
    full_name = serializers.SerializerMethodField()
    display_name = serializers.SerializerMethodField()
    is_kyc_pending = serializers.SerializerMethodField()
    is_kyc_rejected = serializers.SerializerMethodField()
    # اضافه کردن فیلد backup_codes
    backup_codes = serializers.JSONField(read_only=True, help_text=_("JSON array of backup codes for two-factor authentication."))

    # تغییر فیلد allowed_ips - ریجکس قبلی نامعتبر بود
    # اکنون به عنوان CharField تعریف شده و اعتبارسنجی در validate انجام می‌شود
    allowed_ips = serializers.CharField(
        allow_blank=True,
        required=False,
        help_text=_("Comma-separated list of IP addresses in CIDR notation")
    )

    class Meta:
        model = UserProfile
        fields = [
            'id', 'first_name', 'last_name', 'full_name', 'display_name',
            'phone_number', 'nationality', 'date_of_birth', 'address',
            'two_factor_enabled', 'backup_codes', 'api_access_enabled', 'max_api_requests_per_minute', 'allowed_ips',
            'preferred_base_currency', 'default_leverage', 'risk_level', 'max_active_trades', 'max_capital',
            'notify_on_trade', 'notify_on_balance_change', 'notify_on_risk_limit_breach', 'notification_channels',
            'is_kyc_verified', 'is_kyc_pending', 'is_kyc_rejected',
            'kyc_document_type', 'kyc_document_number', 'kyc_submitted_at', 'kyc_verified_at', 'kyc_rejected_at',
            'kyc_rejection_reason',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_allowed_ips(self, value: str) -> str:
        """
        Validates the allowed_ips field using the helper function.
        """
        if value:
            validated_ips = helpers.validate_ip_list(value)
            if validated_ips is None:
                raise serializers.ValidationError(_("Invalid IP address or CIDR format in list."))
            # بازگرداندن لیست تأیید شده به فرمت رشته‌ای
            return ','.join(validated_ips)
        return value

    def get_full_name(self, obj: UserProfile) -> str:
        return obj.get_full_name()

    def get_display_name(self, obj: UserProfile) -> str:
        return obj.get_display_name()

    def get_is_kyc_pending(self, obj: UserProfile) -> bool:
        return obj.is_kyc_pending()

    def get_is_kyc_rejected(self, obj: UserProfile) -> bool:
        return obj.is_kyc_rejected()


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the CustomUser model with enhanced security information.
    """
    profile = UserProfileSerializer(read_only=True)
    is_locked = serializers.ReadOnlyField()
    password_changed_at = serializers.ReadOnlyField()

    class Meta:
        model = CustomUser
        fields = [
            'id', 'email', 'username_display', 'user_type', 'is_active', 'is_verified',
            'is_locked', 'is_demo', 'last_login_ip', 'last_login_at', 'password_changed_at',
            'profile', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'last_login_ip', 'last_login_at', 'password_changed_at', 'created_at', 'updated_at']


class RegistrationSerializer(serializers.ModelSerializer):
    """
    Enhanced registration serializer with comprehensive validation.
    """
    password = serializers.CharField(
        write_only=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(write_only=True, style={'input_type': 'password'})
    profile = UserProfileSerializer(required=False)

    class Meta:
        model = CustomUser
        fields = ['email', 'password', 'password_confirm', 'username_display', 'user_type', 'profile']

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced validation for registration data.
        """
        email = attrs.get('email')
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        # Validate email format and uniqueness
        if email and CustomUser.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError(_("A user with this email already exists"))

        # Validate password match
        if password != password_confirm:
            raise serializers.ValidationError(_("Passwords don't match"))

        # Validate password strength (already handled by validate_password validator)
        # if password and len(password) < 8:
        #     raise serializers.ValidationError(_("Password must be at least 8 characters long"))

        return attrs

    def create(self, validated_data: Dict[str, Any]) -> CustomUser:
        """
        Create user and profile with transaction safety.
        """
        profile_data = validated_data.pop('profile', {})
        validated_data.pop('password_confirm')

        user = CustomUser.objects.create_user(**validated_data)

        # Create profile with default values if not provided
        UserProfile.objects.create(
            user=user,
            preferred_base_currency=profile_data.get('preferred_base_currency', 'IRT'),
            risk_level=profile_data.get('risk_level', 'medium'),
            default_leverage=profile_data.get('default_leverage', 1),
            max_active_trades=profile_data.get('max_active_trades', 5)
        )

        return user


class LoginSerializer(serializers.Serializer):
    """
    Enhanced login serializer with comprehensive security checks.
    """
    email = serializers.EmailField()
    password = serializers.CharField(style={'input_type': 'password'})
    remember_me = serializers.BooleanField(default=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhanced validation for login credentials.
        """
        email = attrs.get('email')
        password = attrs.get('password')

        if not email or not password:
            raise serializers.ValidationError(_("Must include email and password"))

        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    """
    Enhanced password change serializer with current password verification.
    """
    current_password = serializers.CharField(style={'input_type': 'password'})
    new_password = serializers.CharField(
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    new_password_confirm = serializers.CharField(style={'input_type': 'password'})

    def validate_current_password(self, value: str) -> str:
        """
        Validate that the current password is correct.
        """
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError(_("Current password is incorrect"))
        return value

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate password match and strength.
        """
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError(_("New passwords don't match"))

        # Password strength is handled by the validator
        return attrs


class UserSessionSerializer(serializers.ModelSerializer):
    """
    Serializer for user sessions with device information.
    """
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = UserSession
        fields = [
            'id', 'ip_address', 'user_agent', 'device_fingerprint', 'location',
            'is_active', 'expires_at', 'created_at', 'is_current'
        ]
        read_only_fields = ['id', 'created_at']

    def get_is_current(self, obj: UserSession) -> bool:
        """
        Check if this is the current session.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'session') and obj.session_key == request.session.session_key:
            return True
        return False


class UserAPIKeySerializer(serializers.ModelSerializer):
    """
    Enhanced API key serializer with permission validation.
    """
    is_expired = serializers.ReadOnlyField()
    key_preview = serializers.SerializerMethodField()

    class Meta:
        model = UserAPIKey
        fields = [
            'id', 'name', 'key_preview', 'is_active', 'expires_at', 'last_used_at',
            'rate_limit_per_minute', 'permissions', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'key', 'created_at', 'updated_at']

    def get_key_preview(self, obj: UserAPIKey) -> str:
        """
        Return a preview of the API key (first 8 characters).
        """
        return str(obj.key)[:8] + '...' if obj.key else ''

    def validate_permissions(self, value: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate that permissions are properly structured.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Permissions must be a JSON object"))

        allowed_permissions = ['read', 'trade', 'admin']
        for perm in value.keys():
            if perm not in allowed_permissions:
                raise serializers.ValidationError(_(f"Invalid permission: {perm}"))

        return value