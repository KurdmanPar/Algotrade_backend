# apps/risk/views.py
from rest_framework import viewsets, permissions
from .models import (
    RiskProfile,
    RiskRule,
    RiskEvent,
    RiskMetric,
    RiskAlert
)
from .serializers import (
    RiskProfileSerializer,
    RiskRuleSerializer,
    RiskEventSerializer,
    RiskMetricSerializer,
    RiskAlertSerializer
)
from apps.core.views import SecureModelViewSet


class RiskProfileViewSet(SecureModelViewSet):
    queryset = RiskProfile.objects.all()  # اضافه شد
    serializer_class = RiskProfileSerializer


class RiskRuleViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = RiskRule.objects.all()
    serializer_class = RiskRuleSerializer
    permission_classes = [permissions.IsAuthenticated]


class RiskEventViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = RiskEvent.objects.all()
    serializer_class = RiskEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class RiskMetricViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = RiskMetric.objects.all()
    serializer_class = RiskMetricSerializer
    permission_classes = [permissions.IsAuthenticated]


class RiskAlertViewSet(SecureModelViewSet):
    queryset = RiskAlert.objects.all()  # اضافه شد
    serializer_class = RiskAlertSerializer