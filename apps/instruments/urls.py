# apps/instruments/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'instruments', views.InstrumentViewSet, basename='instrument')
router.register(r'instrument-groups', views.InstrumentGroupViewSet, basename='instrument-group')
router.register(r'instrument-categories', views.InstrumentCategoryViewSet, basename='instrument-category')
router.register(r'instrument-exchange-maps', views.InstrumentExchangeMapViewSet, basename='instrument-exchange-maps')

router.register(r'indicators', views.IndicatorViewSet, basename='indicator')
router.register(r'indicator-groups', views.IndicatorGroupViewSet, basename='indicator-groups')
router.register(r'indicator-parameters', views.IndicatorParameterViewSet, basename='indicator-parameter')
router.register(r'indicator-templates', views.IndicatorTemplateViewSet, basename='indicator-template')

router.register(r'price-action-patterns', views.PriceActionPatternViewSet, basename='price-action-pattern')
router.register(r'smart-money-concepts', views.SmartMoneyConceptViewSet, basename='smart-money-concept')
router.register(r'ai-metrics', views.AIMetricViewSet, basename='ai-metric')


urlpatterns = [
    path('', include(router.urls)),
]