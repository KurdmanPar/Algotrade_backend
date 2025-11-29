# apps/agents/views.py
from rest_framework import viewsets, permissions
from .models import AgentType, Agent, AgentInstance, AgentConfig, AgentStatus, AgentMessage, AgentLog, AgentMetric
from .serializers import (
    AgentTypeSerializer, AgentSerializer, AgentInstanceSerializer, AgentConfigSerializer,
    AgentStatusSerializer, AgentMessageSerializer, AgentLogSerializer, AgentMetricSerializer
)
from apps.core.views import SecureModelViewSet

class AgentTypeViewSet(viewsets.ModelViewSet):  # ← اینجا باید تعریف شود
    queryset = AgentType.objects.all()
    serializer_class = AgentTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class AgentViewSet(SecureModelViewSet):
    queryset = Agent.objects.all()
    serializer_class = AgentSerializer

class AgentInstanceViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AgentInstance.objects.all()
    serializer_class = AgentInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentConfigViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AgentConfig.objects.all()
    serializer_class = AgentConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentStatusViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AgentStatus.objects.all()
    serializer_class = AgentStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentMessageViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AgentMessage.objects.all()
    serializer_class = AgentMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AgentLog.objects.all()
    serializer_class = AgentLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentMetricViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AgentMetric.objects.all()
    serializer_class = AgentMetricSerializer
    permission_classes = [permissions.IsAuthenticated]