# apps/instruments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'instrument-groups', views.InstrumentGroupViewSet)
router.register(r'instrument-categories', views.InstrumentCategoryViewSet)
router.register(r'instruments', views.InstrumentViewSet)
router.register(r'instrument-exchange-maps', views.InstrumentExchangeMapViewSet)
router.register(r'indicator-groups', views.IndicatorGroupViewSet)
router.register(r'indicators', views.IndicatorViewSet)
router.register(r'indicator-parameters', views.IndicatorParameterViewSet)
router.register(r'indicator-templates', views.IndicatorTemplateViewSet)
router.register(r'price-action-patterns', views.PriceActionPatternViewSet)
router.register(r'smart-money-concepts', views.SmartMoneyConceptViewSet)
router.register(r'ai-metrics', views.AIMetricViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]