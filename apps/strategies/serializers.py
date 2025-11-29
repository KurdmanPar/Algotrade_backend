# apps/strategies/serializers.py

from rest_framework import serializers
from .models import Strategy

class StrategySerializer(serializers.ModelSerializer):
    owner_email = serializers.EmailField(source='owner.email', read_only=True)

    class Meta:
        model = Strategy
        fields = '__all__'
        read_only_fields = ('owner',) # کاربر را سرور تعیین می‌کند

    def create(self, validated_data):
        # کاربر فعلی را از context بگیر
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)