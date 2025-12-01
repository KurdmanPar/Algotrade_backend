# apps/risk/serializers.py
from rest_framework import serializers
from .models import RiskProfile, RiskRule, RiskEvent, RiskMetric, RiskAlert


class RiskProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskProfile
        fields = '__all__'
        read_only_fields = ('owner',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class RiskRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskRule
        fields = '__all__'


class RiskEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskEvent
        fields = '__all__'


class RiskMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskMetric
        fields = '__all__'


class RiskAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskAlert
        fields = '__all__'