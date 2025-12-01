# apps/logging_app/views.py
from rest_framework import viewsets, permissions
from .models import (
    SystemLog,
    SystemEvent,
    NotificationChannel,
    Alert,
    UserNotificationPreference,
    AuditLog
)
from .serializers import (
    SystemLogSerializer,
    SystemEventSerializer,
    NotificationChannelSerializer,
    AlertSerializer,
    UserNotificationPreferenceSerializer,
    AuditLogSerializer
)
from apps.core.views import SecureModelViewSet


class SystemLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = SystemLog.objects.all()
    serializer_class = SystemLogSerializer
    permission_classes = [permissions.IsAuthenticated]


class SystemEventViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = SystemEvent.objects.all()
    serializer_class = SystemEventSerializer
    permission_classes = [permissions.IsAuthenticated]


class NotificationChannelViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = NotificationChannel.objects.all()
    serializer_class = NotificationChannelSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class AlertViewSet(SecureModelViewSet):
    queryset = Alert.objects.all()  # اضافه شد
    serializer_class = AlertSerializer


class UserNotificationPreferenceViewSet(SecureModelViewSet):
    queryset = UserNotificationPreference.objects.all()  # اضافه شد
    serializer_class = UserNotificationPreferenceSerializer


class AuditLogViewSet(viewsets.ModelViewSet):  # بدون owner
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]