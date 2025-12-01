# apps/signals/views.py
from rest_framework import viewsets, permissions
from .models import Signal, SignalLog, SignalAlert
from .serializers import SignalSerializer, SignalLogSerializer, SignalAlertSerializer
from apps.core.views import SecureModelViewSet


class SignalViewSet(SecureModelViewSet):
    queryset = Signal.objects.all()  # اضافه شد
    serializer_class = SignalSerializer


class SignalLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = SignalLog.objects.all()
    serializer_class = SignalLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class SignalAlertViewSet(SecureModelViewSet):
    queryset = SignalAlert.objects.all()  # اضافه شد
    serializer_class = SignalAlertSerializer