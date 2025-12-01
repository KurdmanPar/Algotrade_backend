# apps/agent_runtime/views.py
from rest_framework import status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from .tasks import run_agent_task
from apps.agents.models import Agent

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def start_agent(request, agent_id):
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        if agent.is_active:
            task = run_agent_task.delay(agent.id)
            return Response({"status": "started", "task_id": task.id}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Agent is not active"}, status=status.HTTP_400_BAD_REQUEST)
    except Agent.DoesNotExist:
        return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def stop_agent(request, agent_id):
    # در عمل، باید یک مکانیزم ارتباطی داشته باشید تا Agent را متوقف کنید (مثلاً با ارسال پیام STOP)
    # در اینجا فقط یک نمونه ساده است.
    try:
        agent = Agent.objects.get(id=agent_id, owner=request.user)
        # اینجا می‌توانید یک پیام STOP به Agent ارسال کنید
        # یا وضعیت را در پایگاه داده تغییر دهید
        agent.is_active = False
        agent.save()
        return Response({"status": "stopped"}, status=status.HTTP_200_OK)
    except Agent.DoesNotExist:
        return Response({"error": "Agent not found"}, status=status.HTTP_404_NOT_FOUND)

# سایر endpointها: pause, resume, logs, metrics و ...