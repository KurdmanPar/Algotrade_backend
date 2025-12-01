# apps/exchanges/serializers.py
from rest_framework import serializers
from .models import Exchange, ExchangeAccount, Wallet, WalletBalance, AggregatedPortfolio, AggregatedAssetPosition


class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = '__all__'


class ExchangeAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeAccount
        fields = '__all__'
        read_only_fields = ('owner',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


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
        read_only_fields = ('owner',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class AggregatedAssetPositionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AggregatedAssetPosition
        fields = '__all__'