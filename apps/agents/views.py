# apps/agents/views.py
from rest_framework import viewsets, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .models import (
    AgentType, Agent, AgentInstance, AgentConfig, AgentStatus, AgentMessage, AgentLog, AgentMetric
)
from .serializers import (
    AgentTypeSerializer, AgentSerializer, AgentInstanceSerializer, AgentConfigSerializer,
    AgentStatusSerializer, AgentMessageSerializer, AgentLogSerializer, AgentMetricSerializer
)
from apps.core.views import SecureModelViewSet

class AgentTypeViewSet(viewsets.ModelViewSet):  # ✅ اضافه شد
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

# API Views برای شروع/توقف
@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_agent(request, agent_id):
    # منطق شروع عامل
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        # فرض بر این است که تسک Celery وجود دارد
        from .tasks import run_agent_task
        run_agent_task.delay(agent.id)
        return Response({'status': 'started'}, status=status.HTTP_200_OK)
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def stop_agent(request, agent_id):
    # منطق توقف عامل
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        agent.is_active = False
        agent.save()
        return Response({'status': 'stopped'}, status=status.HTTP_200_OK)
    except Agent.DoesNotExist:
        return Response({'error': 'Agent not found'}, status=status.HTTP_404_NOT_FOUND)

