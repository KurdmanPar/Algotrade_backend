# apps/logging_app/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'system-logs', views.SystemLogViewSet)
router.register(r'system-events', views.SystemEventViewSet)
router.register(r'notification-channels', views.NotificationChannelViewSet)
router.register(r'alerts', views.AlertViewSet)
router.register(r'user-notification-preferences', views.UserNotificationPreferenceViewSet)
router.register(r'audit-logs', views.AuditLogViewSet)

urlpatterns = [
    path('', include(router.urls)),
]