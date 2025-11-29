# apps/signals/views.py
from rest_framework import viewsets, permissions
from .models import Signal, SignalLog, SignalAlert
from .serializers import *
from apps.core.views import SecureModelViewSet

class SignalViewSet(SecureModelViewSet):
    queryset = Signal.objects.all()  # اضافه شود
    serializer_class = SignalSerializer

class SignalLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = SignalLog.objects.all()
    serializer_class = SignalLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class SignalAlertViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = SignalAlert.objects.all()
    serializer_class = SignalAlertSerializer
    permission_classes = [permissions.IsAuthenticated]