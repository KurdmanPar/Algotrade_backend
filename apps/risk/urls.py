# apps/risk/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'risk-profiles', views.RiskProfileViewSet)
router.register(r'risk-rules', views.RiskRuleViewSet)
router.register(r'risk-events', views.RiskEventViewSet)
router.register(r'risk-metrics', views.RiskMetricViewSet)
router.register(r'risk-alerts', views.RiskAlertViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]