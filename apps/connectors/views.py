# apps/connectors/views.py
from rest_framework import viewsets, permissions
from .models import (
    ExchangeConnectorConfig,
    APICredential,
    ExchangeAPIEndpoint,
    ConnectorSession,
    RateLimitState,
    ConnectorLog,
    ConnectorHealthCheck
)
from .serializers import (
    ExchangeConnectorConfigSerializer,
    APICredentialSerializer,
    ExchangeAPIEndpointSerializer,
    ConnectorSessionSerializer,
    RateLimitStateSerializer,
    ConnectorLogSerializer,
    ConnectorHealthCheckSerializer
)
from apps.core.views import SecureModelViewSet


class ExchangeConnectorConfigViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = ExchangeConnectorConfig.objects.all()
    serializer_class = ExchangeConnectorConfigSerializer
    permission_classes = [permissions.IsAuthenticated]


class APICredentialViewSet(SecureModelViewSet):
    queryset = APICredential.objects.all()  # اضافه شد
    serializer_class = APICredentialSerializer


class ExchangeAPIEndpointViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = ExchangeAPIEndpoint.objects.all()
    serializer_class = ExchangeAPIEndpointSerializer
    permission_classes = [permissions.IsAuthenticated]


class ConnectorSessionViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = ConnectorSession.objects.all()
    serializer_class = ConnectorSessionSerializer
    permission_classes = [permissions.IsAuthenticated]


class RateLimitStateViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = RateLimitState.objects.all()
    serializer_class = RateLimitStateSerializer
    permission_classes = [permissions.IsAuthenticated]


class ConnectorLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = ConnectorLog.objects.all()
    serializer_class = ConnectorLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class ConnectorHealthCheckViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = ConnectorHealthCheck.objects.all()
    serializer_class = ConnectorHealthCheckSerializer
    permission_classes = [permissions.IsAuthenticated]