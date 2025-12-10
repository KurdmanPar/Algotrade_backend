# apps/exchanges/serializers.py

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _
from .models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    OrderHistory,
    MarketDataCandle,
)
from apps.bots.models import TradingBot # فرض بر این است که مدل وجود دارد


class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = '__all__'


class ExchangeAccountSerializer(serializers.ModelSerializer):
    linked_bots = serializers.PrimaryKeyRelatedField(
        queryset=TradingBot.objects.all(),
        many=True,
        required=False,
        help_text=_("List of bot IDs to link to this account.")
    )
    api_key = serializers.CharField(write_only=True, help_text=_("Plain text API key. Will be encrypted."))
    api_secret = serializers.CharField(write_only=True, help_text=_("Plain text API secret. Will be encrypted."))

    class Meta:
        model = ExchangeAccount
        fields = [
            'id', 'user', 'exchange', 'label', 'api_key', 'api_secret', 'extra_credentials',
            'is_active', 'is_paper_trading', 'last_sync_at', 'last_login_ip', 'created_ip',
            'account_info', 'trading_permissions', 'linked_bots',
            # فیلدهای read_only
            'created_at', 'updated_at'
        ]
        read_only_fields = ('user', 'created_at', 'updated_at', 'last_sync_at')

    def create(self, validated_data):
        user = self.context['request'].user
        linked_bots = validated_data.pop('linked_bots', [])
        validated_data['user'] = user

        # مدیریت رمزنگاری کلیدها
        api_key = validated_data.pop('api_key')
        api_secret = validated_data.pop('api_secret')
        instance = super().create(validated_data)
        # فرض بر این است که مدل دارای propertyهای api_key و api_secret است که setter را فراخوانی می‌کند
        instance.api_key = api_key
        instance.api_secret = api_secret
        instance.save()

        if linked_bots:
            instance.linked_bots.set(linked_bots)

        return instance

    def update(self, instance, validated_data):
        linked_bots = validated_data.pop('linked_bots', None)

        # مدیریت به‌روزرسانی کلیدها (اختیاری)
        if 'api_key' in validated_data or 'api_secret' in validated_data:
            api_key = validated_data.pop('api_key', None)
            api_secret = validated_data.pop('api_secret', None)
            if api_key:
                instance.api_key = api_key
            if api_secret:
                instance.api_secret = api_secret

        instance = super().update(instance, validated_data)

        if linked_bots is not None:
            instance.linked_bots.set(linked_bots)

        return instance


class WalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = '__all__'


class WalletBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WalletBalance
        fields = '__all__'


class AggregatedPortfolioSerializer(serializers.ModelSerializer):
    class Meta:
        model = AggregatedPortfolio
        fields = '__all__'
        read_only_fields = ('user',) # کاربر از context تعیین می‌شود

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)


class AggregatedAssetPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AggregatedAssetPosition
        fields = '__all__'


class OrderHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderHistory
        fields = '__all__'
        read_only_fields = ('exchange_account', 'trading_bot') # فرض می‌شود از context یا سایر منطق تعیین می‌شوند


class MarketDataCandleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataCandle
        fields = '__all__'
