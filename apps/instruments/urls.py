# apps/instruments/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'instruments'

# تعریف Router برای ViewSetها
router = DefaultRouter()
router.register(r'instrument-groups', views.InstrumentGroupViewSet, basename='instrumentgroup')
router.register(r'instrument-categories', views.InstrumentCategoryViewSet, basename='instrumentcategory')
router.register(r'instruments', views.InstrumentViewSet, basename='instrument')
router.register(r'instrument-exchange-maps', views.InstrumentExchangeMapViewSet, basename='instrumentexchangemap')

router.register(r'indicator-groups', views.IndicatorGroupViewSet, basename='indicatorgroup')
router.register(r'indicators', views.IndicatorViewSet, basename='indicator')
router.register(r'indicator-parameters', views.IndicatorParameterViewSet, basename='indicatorparameter')
router.register(r'indicator-templates', views.IndicatorTemplateViewSet, basename='indicatortemplate')

router.register(r'price-action-patterns', views.PriceActionPatternViewSet, basename='priceactionpattern')
router.register(r'smart-money-concepts', views.SmartMoneyConceptViewSet, basename='smartmoneyconcept')
router.register(r'ai-metrics', views.AIMetricViewSet, basename='aimetric')

router.register(r'instrument-watchlists', views.InstrumentWatchlistViewSet, basename='instrumentwatchlist')

urlpatterns = [
    # مسیر اصلی شامل تمام مسیرهای تعریف شده در Router
    path('', include(router.urls)),
]

# نکته: اگر از ViewSet استفاده نمی‌کنید و فقط از Viewهای کلاسی یا تابعی استفاده می‌کنید،
# باید مسیرها را به صورت مستقیم با path() تعریف کنید.
# مثال:
# urlpatterns = [
#     path('instruments/', views.InstrumentListCreateView.as_view(), name='instrument-list-create'),
#     path('instruments/<int:pk>/', views.InstrumentRetrieveUpdateDestroyView.as_view(), name='instrument-detail'),
#     # ... سایر مسیرها
# ]
