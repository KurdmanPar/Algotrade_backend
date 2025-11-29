# apps/backtesting/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
# چون queryset اضافه کردیم، دیگر نیازی به مشخص کردن basename نیست
router.register(r'backtest-runs', views.BacktestRunViewSet)
router.register(r'backtest-results', views.BacktestResultViewSet)

urlpatterns = [
    path('', include(router.urls)),
]