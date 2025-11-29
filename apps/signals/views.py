# apps/signals/views.py
from rest_framework import viewsets, permissions
from .models import Signal, SignalLog, SignalAlert
from .serializers import *

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class SignalViewSet(viewsets.ModelViewSet):
    serializer_class = SignalSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Signal.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SignalLogViewSet(viewsets.ModelViewSet):
    queryset = SignalLog.objects.all()
    serializer_class = SignalLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class SignalAlertViewSet(viewsets.ModelViewSet):
    queryset = SignalAlert.objects.all()
    serializer_class = SignalAlertSerializer
    permission_classes = [permissions.IsAuthenticated]
