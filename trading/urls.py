# from django.urls import include, path
# from rest_framework import routers
# from .views import UserViewSet, RoleViewSet, StrategyViewSet, IndicatorViewSet, BotViewSet, TradeViewSet, SignalViewSet
#
# router = routers.DefaultRouter()
# router.register(r'users', UserViewSet)
# router.register(r'roles', RoleViewSet)
# router.register(r'strategies', StrategyViewSet)
# router.register(r'indicators', IndicatorViewSet)
# router.register(r'bots', BotViewSet)
# router.register(r'trades', TradeViewSet)
# router.register(r'signals', SignalViewSet)
#
# urlpatterns = [
#     path('', include(router.urls)),
# ]
#

################################################


# backend/trading/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# ایجاد یک روتر برای ثبت ViewSetها
router = DefaultRouter()

# ثبت UserViewSet با مسیر 'users'
# این کار به طور خودکار نام‌های 'user-list' و 'user-detail' را ایجاد می‌کند
router.register(r'users', views.UserViewSet)
router.register(r'roles', views.RoleViewSet)
router.register(r'strategies', views.StrategyViewSet)
router.register(r'indicators', views.IndicatorViewSet)
router.register(r'bots', views.BotViewSet)
router.register(r'trades', views.TradeViewSet)
router.register(r'signals', views.SignalViewSet)



# URLهای اپلیکیشن
urlpatterns = [
    # مسیر ورود برای دریافت توکن
    path('api-token-auth/', views.CustomObtainAuthToken.as_view()),
    # URLهای تولید شده توسط روتر
    path('', include(router.urls)),
]
