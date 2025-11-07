# backend/trading/serializers.py

from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Role, Strategy, Indicator, Bot, Trade, Signal

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل کاربر.
    - فیلد password فقط برای نوشتن است و در خروجی نمایش داده نمی‌شود.
    - متد create بازنویسی شده تا رمز عبور را به صورت امن هش کند.
    """
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name', 'password', 'balance', 'is_trader']
        read_only_fields = ['id', 'balance']

    def create(self, validated_data):
        """
        متد create برای ایجاد کاربر با رمز عبور هش شده.
        """
        password = validated_data.pop('password', None)
        user = super().create(validated_data)
        if password:
            user.set_password(password)
            user.save()
        return user

# --- سریالایزرهای دیگر که به آن‌ها نیاز داریم ---

class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = '__all__'

class StrategySerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل استراتژی.
    - فیلد owner فقط خواندنی است و آیدی کاربر را برمی‌گرداند.
    """
    # این فیلد فقط خواندنی است و آیدی کاربر را برمی‌گرداند
    owner = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Strategy
        fields = '__all__'
        # نیازی به read_only_fields نیست چون خود فیلد read_only تعریف شده

class IndicatorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Indicator
        fields = '__all__'


class BotSerializer(serializers.ModelSerializer):
    """
    سریالایزر برای مدل بات.
    - فیلدهای user و strategy فقط خواندنی هستند و آیدی مربوطه را برمی‌گردانند.
    """
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    strategy = serializers.PrimaryKeyRelatedField(queryset=Strategy.objects.all())

    class Meta:
        model = Bot
        fields = '__all__'
        # نیازی به read_only_fields نیست چون خود فیلدها read_only تعریف شده‌اند

# ... سایر سریالایزرها ...


class TradeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trade
        fields = '__all__'

class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = '__all__'
