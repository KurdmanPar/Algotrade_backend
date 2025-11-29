# apps/strategies/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# مشخص کردن basename به صورت صریح
router.register(r'strategies', views.StrategyViewSet, basename='strategy')

urlpatterns = [
   path('api/', include(router.urls)),
]
