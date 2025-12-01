# apps/bots/views.py
from rest_framework import viewsets, permissions
from .models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot
from .serializers import (
    BotSerializer, BotStrategyConfigSerializer, BotLogSerializer, BotPerformanceSnapshotSerializer
)
from apps.core.views import SecureModelViewSet  # فرض بر این است که کلاس امنیتی شما به این صورت است


class BotViewSet(SecureModelViewSet):
    queryset = Bot.objects.all()
    serializer_class = BotSerializer

    # اگر مدل Bot دارای فیلد owner باشد، SecureModelViewSet این را خودش مدیریت می‌کند


class BotStrategyConfigViewSet(viewsets.ModelViewSet):  # این مدل فیلد owner ندارد، پس فقط ModelViewSet
    queryset = BotStrategyConfig.objects.all()
    serializer_class = BotStrategyConfigSerializer
    permission_classes = [permissions.IsAuthenticated]


class BotLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = BotLog.objects.all()
    serializer_class = BotLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class BotPerformanceSnapshotViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = BotPerformanceSnapshot.objects.all()
    serializer_class = BotPerformanceSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated]