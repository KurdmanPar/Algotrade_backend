# apps/logging_app/views.py
from rest_framework import viewsets, permissions
from .models import SystemLog, SystemEvent, NotificationChannel, Alert, UserNotificationPreference, AuditLog
from .serializers import *

class IsOwnerOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if hasattr(obj, 'owner'):
            return obj.owner == request.user
        elif hasattr(obj, 'user'):
            return obj.user == request.user
        return True

class SystemLogViewSet(viewsets.ModelViewSet):
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAuthenticated]

class SystemEventViewSet(viewsets.ModelViewSet):
    queryset = SystemEvent.objects.all()
    serializer_class = SystemEventSerializer
    permission_classes = [permissions.IsAuthenticated]

class NotificationChannelViewSet(viewsets.ModelViewSet):
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Alert.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user=user)

class UserNotificationPreferenceViewSet(viewsets.ModelViewSet):
    queryset = UserNotificationPreference.objects.all()
    serializer_class = UserNotificationPreferenceSerializer
    permission_classes = [permissions.IsAuthenticated]

class AuditLogViewSet(viewsets.ModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]