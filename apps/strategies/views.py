# apps/strategies/views.py
from rest_framework import viewsets, permissions
from .models import Strategy, StrategyVersion, StrategyAssignment
from .serializers import StrategySerializer, StrategyVersionSerializer, StrategyAssignmentSerializer
from apps.core.views import SecureModelViewSet


class StrategyViewSet(SecureModelViewSet):
    queryset = Strategy.objects.all()  # اضافه شد
    serializer_class = StrategySerializer


class StrategyVersionViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = StrategyVersion.objects.all()
    serializer_class = StrategyVersionSerializer
    permission_classes = [permissions.IsAuthenticated]


class StrategyAssignmentViewSet(SecureModelViewSet):
    queryset = StrategyAssignment.objects.all()  # اضافه شد
    serializer_class = StrategyAssignmentSerializer