# apps/strategies/serializers.py
from rest_framework import serializers
from .models import Strategy, StrategyVersion, StrategyAssignment

class StrategySerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Strategy
        fields = '__all__'
        read_only_fields = ('owner',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)

class StrategyVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyVersion
        fields = '__all__'

class StrategyAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StrategyAssignment
        fields = '__all__'