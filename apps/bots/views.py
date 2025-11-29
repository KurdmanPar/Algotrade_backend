# apps/bots/views.py
from rest_framework import viewsets, permissions
from .models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot
from .serializers import *
from apps.core.views import SecureModelViewSet

class BotViewSet(SecureModelViewSet):
    queryset = Bot.objects.all()  # اضافه شود
    serializer_class = BotSerializer

class BotStrategyConfigViewSet(SecureModelViewSet):
    queryset = BotStrategyConfig.objects.all()  # اضافه شود
    serializer_class = BotStrategyConfigSerializer

class BotLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = BotLog.objects.all()
    serializer_class = BotLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class BotPerformanceSnapshotViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = BotPerformanceSnapshot.objects.all()
    serializer_class = BotPerformanceSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]