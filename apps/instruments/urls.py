# apps/instruments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'instruments', views.InstrumentViewSet)
router.register(r'indicators', views.IndicatorViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]