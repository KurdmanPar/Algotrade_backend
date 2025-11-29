# apps/agents/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'agent-types', views.AgentTypeViewSet)  # ← اینجا داریم دنبال AgentTypeViewSet می‌گردیم
router.register(r'agents', views.AgentViewSet)
router.register(r'agent-configs', views.AgentConfigViewSet)
router.register(r'agent-statuses', views.AgentStatusViewSet)
router.register(r'agent-messages', views.AgentMessageViewSet)
router.register(r'agent-logs', views.AgentLogViewSet)
router.register(r'agent-metrics', views.AgentMetricViewSet)

urlpatterns = [
    path('', include(router.urls)),
]