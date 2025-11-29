# apps/bots/views.py
from rest_framework import viewsets, permissions
from .models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot
from .serializers import *

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class BotViewSet(viewsets.ModelViewSet):
    serializer_class = BotSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Bot.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class BotStrategyConfigViewSet(viewsets.ModelViewSet):
    queryset = BotStrategyConfig.objects.all()
    serializer_class = BotStrategyConfigSerializer
    permission_classes = [permissions.IsAuthenticated]

class BotLogViewSet(viewsets.ModelViewSet):
    queryset = BotLog.objects.all()
    serializer_class = BotLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class BotPerformanceSnapshotViewSet(viewsets.ModelViewSet):
    queryset = BotPerformanceSnapshot.objects.all()
    serializer_class = BotPerformanceSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]