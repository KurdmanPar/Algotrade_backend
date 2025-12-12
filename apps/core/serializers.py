# apps/core/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
)

# --- سریالایزر پایه (Base Serializer) ---
class CoreBaseSerializer(serializers.ModelSerializer):
    """
    Serializer پایه برای تمام سریالایزرها در اپلیکیشن core یا سایر اپلیکیشن‌هایی که از مدل‌های پایه core استفاده می‌کنند.
    این سریالایزر فیلدهای مشترکی مانند id، created_at و updated_at را مدیریت می‌کند.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        # مدل پایه برای نمایش فیلدهای مشترک است
        # این کلاس انتزاعی است و نباید مستقیماً برای یک مدل خاص استفاده شود مگر اینکه منطقی داشته باشد
        model = BaseModel # استفاده از مدل انتزاعی برای این سریالایزر نیز انتزاعی است
        fields = ['id', 'created_at', 'updated_at']
        abstract = True # این سریالایزر انتزاعی است


class CoreOwnedModelSerializer(CoreBaseSerializer):
    """
    Serializer پایه برای مدل‌هایی که دارای فیلد owner هستند (ارث‌بری از BaseOwnedModel).
    """
    # owner را به صورت فقط خواندنی نمایش می‌دهد
    # owner = serializers.PrimaryKeyRelatedField(read_only=True)
    # یا نام کاربری مالک را نشان می‌دهد
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta(CoreBaseSerializer.Meta):
        # model = BaseOwnedModel # این هم انتزاعی است
        fields = CoreBaseSerializer.Meta.fields + ['owner', 'owner_username'] # فرض: مدل دارای فیلد owner است
        abstract = True

    def create(self, validated_data):
        """
        در هنگام ایجاد شیء، فیلد owner را به کاربر فعلی (request.user) تنظیم می‌کند.
        توجه: این کار فقط زمانی انجام می‌شود که 'owner' در validated_data وجود نداشته باشد.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user') and 'owner' not in validated_data:
            validated_data['owner'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        در هنگام بروزرسانی، جلوی تغییر فیلد owner را می‌گیرد مگر اینکه منطق خاصی نیاز به آن داشته باشد.
        """
        validated_data.pop('owner', None) # حذف owner از داده‌های تأیید شده
        return super().update(instance, validated_data)


class TimeStampedModelSerializer(serializers.ModelSerializer):
    """
    Serializer پایه برای مدل‌هایی که دارای فیلدهای created_at و updated_at هستند (ارث‌بری از TimeStampedModel).
    این سریالایزر فقط فیلدهای زمانی را شامل می‌شود.
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = TimeStampedModel
        fields = ['created_at', 'updated_at']
        abstract = True # این سریالایزر انتزاعی است


# --- سریالایزرها برای مدل‌های Core ---


class AuditLogSerializer(serializers.ModelSerializer):
    """
    Serializer for the AuditLog model.
    """
    # اضافه کردن نام کاربری به جای نمایش فقط ID
    user_email = serializers.CharField(source='user.email', read_only=True)
    # فیلدی برای نمایش خلاصه ای از جزئیات (در صورت نیاز)
    details_summary = serializers.SerializerMethodField()

    class Meta:
        model = AuditLog
        fields = [
            'id', 'user', 'user_email', 'action', 'target_model', 'target_id', 'details', 'details_summary',
            'ip_address', 'user_agent', 'session_key', 'created_at'
        ]
        read_only_fields = ['id', 'created_at', 'user'] # کاربر باید از context گرفته شود

    def get_details_summary(self, obj):
        """
        یک خلاصه از جزئیات برای نمایش سریع.
        """
        details = obj.details
        if isinstance(details, dict):
            return ', '.join([f"{k}: {v}" for k, v in list(details.items())[:3]]) # نمایش 3 مورد اول
        return str(details)[:100] # اگر رشته بود، 100 کاراکتر اول

    def create(self, validated_data):
        """
        اطمینان از اینکه فیلد user از context گرفته شود.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['user'] = request.user
        else:
            # یا یک مقدار پیش‌فرض قرار دهید یا خطایی ایجاد کنید
            # validated_data['user'] = None # این ممکن است باعث خطا شود اگر فیلد null=False باشد
            pass # یا افزودن یک اعتبارسنجی در validate
        return super().create(validated_data)


class SystemSettingSerializer(serializers.ModelSerializer):
    """
    Serializer for the SystemSetting model.
    Includes validation for the data type and sensitive data handling.
    """
    class Meta:
        model = SystemSetting
        fields = [
            'id', 'key', 'value', 'description', 'data_type', 'is_sensitive', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_value(self, value):
        """
        Validates the value based on its declared data_type.
        """
        # توجه: self.instance فقط در هنگام بروزرسانی (update) وجود دارد
        # برای ایجاد (create)، باید data_type از validated_data گرفته شود
        data_type = self.instance.data_type if self.instance else self.initial_data.get('data_type')

        if not data_type:
            # اگر data_type از هیچ کجایی گرفته نشد، نمی‌توان اعتبارسنجی کرد
            return value

        if data_type == 'int':
            try:
                int(value)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Value must be a valid integer for data type 'int'.")
        elif data_type == 'float':
            try:
                float(value)
            except (ValueError, TypeError):
                raise serializers.ValidationError("Value must be a valid float for data type 'float'.")
        elif data_type == 'bool':
            if value.lower() not in ['true', 'false', '1', '0']:
                raise serializers.ValidationError("Value must be 'true', 'false', '1', or '0' for data type 'bool'.")
        elif data_type == 'json':
            import json
            try:
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Value must be a valid JSON string for data type 'json'.")

        return value

    def to_representation(self, instance):
        """
        Hides the value if the setting is marked as sensitive.
        """
        data = super().to_representation(instance)
        if instance.is_sensitive:
            data['value'] = "***" # یا یک مقدار مسک شده
        return data


class CacheEntrySerializer(serializers.ModelSerializer):
    """
    Serializer for the CacheEntry model.
    """
    class Meta:
        model = CacheEntry
        fields = [
            'id', 'key', 'value', 'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def validate_key(self, value):
        """
        Validates the cache key format (e.g., length, allowed characters).
        """
        if len(value) > 255:
            raise serializers.ValidationError("Cache key cannot exceed 255 characters.")
        # می‌توانید الگوی regex برای محدود کردن کاراکترها نیز اضافه کنید
        # if not re.match(r'^[a-zA-Z0-9_]+$', value):
        #     raise serializers.ValidationError("Cache key can only contain letters, numbers, and underscores.")
        return value

    def validate(self, attrs):
        """
        Validates the expiration time.
        """
        expires_at = attrs.get('expires_at')
        if expires_at and expires_at < timezone.now():
            raise serializers.ValidationError({"expires_at": "Expiration time cannot be in the past."})
        return attrs

    def to_representation(self, instance):
        """
        Optionally mask sensitive parts of the value if it's known to be sensitive.
        This is a simple example. In practice, you might need a more sophisticated check
        based on the 'key' or a dedicated flag on the model.
        """
        data = super().to_representation(instance)
        # فرض: اگر کلید شامل 'api_key' بود، مقدار را مسک کن
        if 'api_key' in instance.key.lower():
            data['value'] = "***" # یا تابع mask کمکی استفاده شود
        return data

# --- سایر سریالایزرهای پایه ---
# می‌توانید سریالایزرهای دیگری مانند یک BaseReadSerializer یا BaseWriteSerializer نیز در اینجا تعریف کنید
# که در اپلیکیشن‌های دامنه‌ای مانند instruments استفاده شوند.

class BaseReadSerializer(serializers.ModelSerializer):
    """
    Serializer base class for read operations (list, retrieve).
    Can include fields like owner_username which are useful for display.
    """
    owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        abstract = True
        fields = '__all__' # یا فیلدهای مشخصی

class BaseWriteSerializer(serializers.ModelSerializer):
    """
    Serializer base class for write operations (create, update).
    Can exclude sensitive fields or handle owner assignment.
    """
    class Meta:
        abstract = True
        fields = '__all__' # یا فیلدهای مشخصی

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and 'owner' in self.Meta.model._meta.fields:
            validated_data['owner'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        validated_data.pop('owner', None) # جلوگیری از تغییر owner
        return super().update(instance, validated_data)
