# apps/risk/views.py
from rest_framework import viewsets, permissions
from .models import RiskProfile, RiskRule, RiskEvent, RiskMetric, RiskAlert
from .serializers import *

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class RiskProfileViewSet(viewsets.ModelViewSet):
    serializer_class = RiskProfileSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return RiskProfile.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

class RiskRuleViewSet(viewsets.ModelViewSet):
    queryset = RiskRule.objects.all()
    serializer_class = RiskRuleSerializer
    permission_classes = [permissions.IsAuthenticated]

class RiskEventViewSet(viewsets.ModelViewSet):
    queryset = RiskEvent.objects.all()
    serializer_class = RiskEventSerializer
    permission_classes = [permissions.IsAuthenticated]

class RiskMetricViewSet(viewsets.ModelViewSet):
    queryset = RiskMetric.objects.all()
    serializer_class = RiskMetricSerializer
    permission_classes = [permissions.IsAuthenticated]

class RiskAlertViewSet(viewsets.ModelViewSet):
    queryset = RiskAlert.objects.all()
    serializer_class = RiskAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
