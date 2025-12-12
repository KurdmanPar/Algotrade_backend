# apps/core/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'core'

# تعریف Router برای ViewSetها
router = DefaultRouter()
router.register(r'audit-logs', views.AuditLogViewSet, basename='auditlog')
router.register(r'system-settings', views.SystemSettingViewSet, basename='systemsetting')
router.register(r'cache-entries', views.CacheEntryViewSet, basename='cacheentry')
# اگر مدل‌های دیگری داشته باشید، آن‌ها را نیز اینجا ثبت کنید
# router.register(r'log-events', views.LogEventViewSet, basename='logevent')
# router.register(r'scheduled-tasks', views.ScheduledTaskViewSet, basename='scheduledtask')

urlpatterns = [
    # مسیر اصلی شامل تمام مسیرهای تعریف شده در Router
    path('', include(router.urls)),

    # مسیرهای اختصاصی می‌توانند در اینجا اضافه شوند
    # مثلاً یک اندپوینت عمومی برای چک سلامت
    path('health-check/', views.HealthCheckView.as_view(), name='health-check'),
    path('ping/', views.PingView.as_view(), name='ping'),

    # مسیرهای مرتبط با مدیریت کلی سیستم (اگر در ادمین نباشد)
    # path('system-status/', views.SystemStatusView.as_view(), name='system-status'),

]

# نکته: اگر از ViewSet استفاده نمی‌کنید و فقط از Viewهای کلاسی یا تابعی استفاده می‌کنید،
# باید مسیرها را به صورت مستقیم با path() تعریف کنید.
# مثال:
# urlpatterns = [
#     path('audit-log/', views.AuditLogListCreateView.as_view(), name='audit-log-list-create'),
#     path('audit-log/<uuid:pk>/', views.AuditLogRetrieveUpdateDestroyView.as_view(), name='audit-log-detail'),
#     # ... سایر مسیرها
# ]
