# apps/connectors/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'exchange-connector-configs', views.ExchangeConnectorConfigViewSet)
router.register(r'api-credentials', views.APICredentialViewSet)
router.register(r'exchange-api-endpoints', views.ExchangeAPIEndpointViewSet)
router.register(r'connector-sessions', views.ConnectorSessionViewSet)
router.register(r'rate-limit-states', views.RateLimitStateViewSet)
router.register(r'connector-logs', views.ConnectorLogViewSet)
router.register(r'connector-health-checks', views.ConnectorHealthCheckViewSet)

urlpatterns = [
    path('', include(router.urls)),
]