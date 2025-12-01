# apps/backtesting/serializers.py
from rest_framework import serializers
from .models import BacktestRun, BacktestResult


class BacktestRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestRun
        fields = '__all__'
        read_only_fields = ('owner',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class BacktestResultSerializer(serializers.ModelSerializer):
    class Meta:
        model = BacktestResult
        fields = '__all__'