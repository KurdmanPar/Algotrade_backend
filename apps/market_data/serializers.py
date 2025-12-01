# apps/market_data/serializers.py
from rest_framework import serializers
from .models import DataSource, MarketDataConfig, MarketDataSnapshot, MarketDataSyncLog


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = '__all__'


class MarketDataConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataConfig
        fields = '__all__'


class MarketDataSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataSnapshot
        fields = '__all__'


class MarketDataSyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketDataSyncLog
        fields = '__all__'