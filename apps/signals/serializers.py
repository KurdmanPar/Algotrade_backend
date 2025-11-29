# apps/signals/serializers.py
from rest_framework import serializers
from .models import Signal, SignalLog, SignalAlert

class SignalSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signal
        fields = '__all__'
        read_only_fields = ('user',)

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['user'] = user
        return super().create(validated_data)

class SignalLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalLog
        fields = '__all__'

class SignalAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SignalAlert
        fields = '__all__'