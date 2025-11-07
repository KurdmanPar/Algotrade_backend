from django.urls import include, path
from rest_framework import routers
from .views import UserViewSet, RoleViewSet, StrategyViewSet, IndicatorViewSet, BotViewSet, TradeViewSet, SignalViewSet

router = routers.DefaultRouter()
router.register(r'users', UserViewSet)
router.register(r'roles', RoleViewSet)
router.register(r'strategies', StrategyViewSet)
router.register(r'indicators', IndicatorViewSet)
router.register(r'bots', BotViewSet)
router.register(r'trades', TradeViewSet)
router.register(r'signals', SignalViewSet)

urlpatterns = [
    path('', include(router.urls)),
]
