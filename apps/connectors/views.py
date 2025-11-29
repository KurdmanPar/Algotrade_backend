# apps/connectors/views.py
from rest_framework import viewsets, permissions
from .models import (
    ExchangeConnectorConfig, APICredential, ExchangeAPIEndpoint,
    ConnectorSession, RateLimitState, ConnectorLog, ConnectorHealthCheck
)
from .serializers import *

class ConnectorViewSetBase:
    permission_classes = [permissions.IsAuthenticated]

class ExchangeConnectorConfigViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = ExchangeConnectorConfig.objects.all()
    serializer_class = ExchangeConnectorConfigSerializer

class APICredentialViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = APICredential.objects.all()
    serializer_class = APICredentialSerializer

class ExchangeAPIEndpointViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = ExchangeAPIEndpoint.objects.all()
    serializer_class = ExchangeAPIEndpointSerializer

class ConnectorSessionViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = ConnectorSession.objects.all()
    serializer_class = ConnectorSessionSerializer

class RateLimitStateViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = RateLimitState.objects.all()
    serializer_class = RateLimitStateSerializer

class ConnectorLogViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = ConnectorLog.objects.all()
    serializer_class = ConnectorLogSerializer

class ConnectorHealthCheckViewSet(viewsets.ModelViewSet, ConnectorViewSetBase):
    queryset = ConnectorHealthCheck.objects.all()
    serializer_class = ConnectorHealthCheckSerializer