# apps/strategies/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'strategies', views.StrategyViewSet)
router.register(r'strategy-versions', views.StrategyVersionViewSet)
router.register(r'strategy-assignments', views.StrategyAssignmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
]