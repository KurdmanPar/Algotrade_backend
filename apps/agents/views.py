# apps/agents/views.py
from rest_framework import viewsets, permissions
from .models import AgentType, Agent, AgentInstance, AgentConfig, AgentStatus, AgentMessage, AgentLog, AgentMetric
from .serializers import *

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class AgentTypeViewSet(viewsets.ModelViewSet):
    queryset = AgentType.objects.all()
    serializer_class = AgentTypeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class AgentViewSet(viewsets.ModelViewSet):
    serializer_class = AgentSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Agent.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(owner=user, created_by=user)

class AgentInstanceViewSet(viewsets.ModelViewSet):
    queryset = AgentInstance.objects.all()
    serializer_class = AgentInstanceSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentConfigViewSet(viewsets.ModelViewSet):
    queryset = AgentConfig.objects.all()
    serializer_class = AgentConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentStatusViewSet(viewsets.ModelViewSet):
    queryset = AgentStatus.objects.all()
    serializer_class = AgentStatusSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentMessageViewSet(viewsets.ModelViewSet):
    queryset = AgentMessage.objects.all()
    serializer_class = AgentMessageSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentLogViewSet(viewsets.ModelViewSet):
    queryset = AgentLog.objects.all()
    serializer_class = AgentLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class AgentMetricViewSet(viewsets.ModelViewSet):
    queryset = AgentMetric.objects.all()
    serializer_class = AgentMetricSerializer
    permission_classes = [permissions.IsAuthenticated]