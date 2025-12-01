# apps/connectors/serializers.py
from rest_framework import serializers
from .models import (
    ExchangeConnectorConfig, APICredential, ExchangeAPIEndpoint,
    ConnectorSession, RateLimitState, ConnectorLog, ConnectorHealthCheck
)


class ExchangeConnectorConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeConnectorConfig
        fields = '__all__'


class APICredentialSerializer(serializers.ModelSerializer):
    class Meta:
        model = APICredential
        fields = '__all__'
        # فیلدهای حساس را می‌توان در read_only قرار داد یا کلاً حذف کرد
        extra_kwargs = {
            'api_secret_encrypted': {'write_only': True},
            'credentials_encrypted': {'write_only': True}
        }


class ExchangeAPIEndpointSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExchangeAPIEndpoint
        fields = '__all__'


class ConnectorSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorSession
        fields = '__all__'


class RateLimitStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RateLimitState
        fields = '__all__'


class ConnectorLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorLog
        fields = '__all__'


class ConnectorHealthCheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConnectorHealthCheck
        fields = '__all__'