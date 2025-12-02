# apps/signals/serializers.py
"""
سریالایزرهای امن برای اپلیکیشن signals
تمام سریالایزرها با اعتبارسنجی دقیق و فیلد‌های محدود طراحی شده‌اند
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from .models import Signal, SignalLog, SignalAlert


# ============================================
# Signal Serializer
# ============================================

class SignalSerializer(serializers.ModelSerializer):
    """
    سریالایزر امن برای ایجاد و نمایش سیگنال‌ها
    فقط فیلدهای مجاز از API قابل دسترسی هستند
    """

    # کاربر به صورت خودکار از request گرفته می‌شود
    user = serializers.PrimaryKeyRelatedField(
        read_only=True,
        default=serializers.CurrentUserDefault()
    )

    # status فقط‌خواندنی - فقط توسط سیستم تغییر می‌کند
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Signal
        fields = [
            'id', 'user', 'bot', 'strategy_version', 'agent',
            'exchange_account', 'instrument', 'direction', 'signal_type',
            'quantity', 'price', 'confidence_score', 'payload',
            'status', 'priority', 'is_recurring', 'generated_at', 'expires_at'
        ]

        # فیلدهای فقط‌خواندنی از API
        read_only_fields = [
            'id', 'user', 'status', 'created_at', 'updated_at',
            'sent_to_risk', 'sent_to_execution', 'correlation_id',
            'executed_at', 'processed_at'
        ]

    def validate(self, attrs):
        """
        اعتبارسنجی امن سطح سریالایزر
        جلوگیری از spoofing و injection
        """
        request = self.context.get('request')
        if not request or not request.user:
            raise serializers.ValidationError(_("درخواست معتبر نیست"))

        user = request.user

        # اطمینان از اینکه agent متعلق به کاربر است
        agent = attrs.get('agent')
        if agent and hasattr(agent, 'user') and agent.user != user:
            raise serializers.ValidationError({
                'agent': _("Agent انتخابی متعلق به شما نیست")
            })

        # چک کردن حساب صرافی
        exchange_account = attrs.get('exchange_account')
        if exchange_account and hasattr(exchange_account, 'user') and exchange_account.user != user:
            raise serializers.ValidationError({
                'exchange_account': _("Exchange Account متعلق به شما نیست")
            })

        # اعتبارسنجی instrument
        instrument = attrs.get('instrument')
        if instrument and exchange_account and hasattr(instrument, 'exchange'):
            if instrument.exchange != exchange_account.exchange:
                raise serializers.ValidationError({
                    'instrument': _("Instrument با Exchange Account سازگار نیست")
                })

        # اعتبارسنجی quantity مثبت
        if attrs.get('quantity', 0) <= 0:
            raise serializers.ValidationError({
                'quantity': _("Quantity باید بزرگتر از صفر باشد")
            })

        # اعتبارسنجی confidence_score بین 0-1
        confidence = attrs.get('confidence_score', 0)
        if not (0 <= confidence <= 1):
            raise serializers.ValidationError({
                'confidence_score': _("Confidence Score باید بین 0 و 1 باشد")
            })

        return attrs

    def create(self, validated_data):
        """
        ایجاد سیگنال با اطلاعات امنیتی اضافی
        """
        request = self.context.get('request')

        # اضافه کردن اطلاعات امنیتی
        validated_data['created_by_ip'] = self._get_client_ip(request)
        validated_data['user_agent'] = request.META.get('HTTP_USER_AGENT', '')[:512]

        return super().create(validated_data)

    def _get_client_ip(self, request):
        """استخراج IP امن از request"""
        if not request:
            return None

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        return request.META.get('REMOTE_ADDR')


# ============================================
# SignalLog Serializer (فقط‌خواندنی)
# ============================================

class SignalLogSerializer(serializers.ModelSerializer):
    """
    سریالایزر فقط‌خواندنی برای لاگ‌ها
    لاگ‌ها نباید از API قابل ایجاد یا ویرایش باشند
    """

    class Meta:
        model = SignalLog
        fields = [
            'id', 'signal', 'old_status', 'new_status',
            'message', 'details', 'changed_by_agent', 'changed_by_user',
            'created_at'
        ]

        # همه فیلدها فقط‌خواندنی هستند
        read_only_fields = fields

    def create(self, validated_data):
        """غیرفعال کردن ایجاد از API"""
        raise serializers.ValidationError(_("ایجاد لاگ از API مجاز نیست"))

    def update(self, instance, validated_data):
        """غیرفعال کردن ویرایش از API"""
        raise serializers.ValidationError(_("ویرایش لاگ از API مجاز نیست"))


# ============================================
# SignalAlert Serializer
# ============================================

class SignalAlertSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای نمایش هشدارها
    فقط نمایش و تایید مجاز است
    """

    class Meta:
        model = SignalAlert
        fields = [
            'id', 'signal', 'alert_type', 'severity', 'title',
            'description', 'details', 'is_acknowledged',
            'acknowledged_at', 'acknowledged_by', 'created_at'
        ]

        # فیلدهای فقط‌خواندنی
        read_only_fields = [
            'id', 'signal', 'alert_type', 'severity', 'title',
            'description', 'details', 'created_at', 'updated_at',
            'acknowledged_at', 'acknowledged_by'
        ]

    def update(self, instance, validated_data):
        """
        فقط تایید هشدار مجاز است
        """
        if 'is_acknowledged' in validated_data:
            request = self.context.get('request')
            if request and request.user:
                instance.acknowledge(request.user, self._get_client_ip(request))
                return instance

        raise serializers.ValidationError(_("فقط تایید هشدار مجاز است"))

    def _get_client_ip(self, request):
        """استخراج IP امن از request"""
        if not request:
            return None

        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR', '')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()

        return request.META.get('REMOTE_ADDR')