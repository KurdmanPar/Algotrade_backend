# apps/core/views.py

from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌های احتمالی core
    # InstrumentGroup,
    # InstrumentCategory,
    # Instrument,
    # InstrumentExchangeMap,
    # IndicatorGroup,
    # Indicator,
    # IndicatorParameter,
    # IndicatorTemplate,
    # PriceActionPattern,
    # SmartMoneyConcept,
    # AIMetric,
    # InstrumentWatchlist,
)
from .serializers import (
    CoreBaseSerializer,
    CoreOwnedModelSerializer,
    TimeStampedModelSerializer,
    AuditLogSerializer,
    SystemSettingSerializer,
    CacheEntrySerializer,
    # BaseReadSerializer,
    # BaseWriteSerializer,
    # سایر سریالایزرهایی که در core تعریف کرده‌اید
)
from .permissions import IsOwnerOrReadOnly, IsOwnerOfRelatedObject, IsAdminUserOrReadOnly, IsVerifiedUser, IsPublicOrOwner, IsOwnerOfWatchlist
from .exceptions import CoreSystemException, DataIntegrityException, ConfigurationError
from .services import CoreService, AuditService, SecurityService
from .helpers import get_client_ip, generate_device_fingerprint
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد
from apps.instruments.models import Instrument # فرض بر این است که مدل نماد وجود دارد
from apps.exchanges.models import Exchange # فرض بر این است که مدل صرافی وجود دارد
from apps.bots.models import TradingBot # فرض بر این است که مدل بات وجود دارد
from apps.risk.models import RiskRule # فرض بر این است که مدل قانون ریسک وجود دارد

User = get_user_model()

# --- نماهای عمومی (Public Views) ---
class HealthCheckView(APIView):
    """
    نمای ساده برای چک کردن سلامت سیستم.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # می‌توانید چک‌های ساده‌ای مانند ping پایگاه داده یا کش اضافه کنید
        # db_ok = ...
        # cache_ok = ...
        # if not (db_ok and cache_ok):
        #     return Response({"status": "unhealthy", "details": {...}}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        return Response({"status": "ok", "timestamp": timezone.now()}, status=status.HTTP_200_OK)

class PingView(APIView):
    """
    نمای ساده برای پینگ کردن سرور.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_ip = get_client_ip(request)
        return Response({"pong": timezone.now(), "client_ip": client_ip}, status=status.HTTP_200_OK)

# --- نماهای پایه (Base Views) ---

class SecureModelViewSet(viewsets.ModelViewSet):
    """
    ViewSet پایه امن برای مدل‌هایی که دارای فیلدهای زمان‌بندی و مالکیت هستند.
    این ViewSet از اجازه‌نامه‌های پایه و فیلترهای مشترک استفاده می‌کند.
    """
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        """
        اگر مدل دارای فیلد 'is_active' باشد، فقط آیتم‌های فعال را برمی‌گرداند.
        اگر مدل از BaseOwnedModel ارث می‌برد، فقط آیتم‌های متعلق به کاربر فعلی را برمی‌گرداند.
        """
        qs = super().get_queryset()

        # فیلتر بر اساس is_active اگر وجود داشت
        if hasattr(qs.model, 'is_active'):
            qs = qs.filter(is_active=True)

        # فیلتر بر اساس مالک (owner) اگر وجود داشت
        if hasattr(qs.model, 'owner'):
            user = self.request.user
            if not user.is_authenticated:
                # اگر کاربر احراز هویت نشده باشد، مجموعه خالی برگردانده می‌شود
                return qs.none()
            qs = qs.filter(owner=user)

        return qs

    def perform_create(self, serializer):
        """
        اگر مدل دارای فیلد 'owner' باشد، فیلد owner را به کاربر فعلی تنظیم می‌کند.
        """
        user = self.request.user
        if hasattr(serializer.Meta.model, 'owner') and user.is_authenticated:
            serializer.save(owner=user)
        else:
            serializer.save()

    def perform_update(self, serializer):
        """
        اطمینان از اینکه کاربر فقط می‌تواند شیء خود را ویرایش کند.
        """
        # اجازه‌نامه IsOwnerOrReadOnly باید این کار را انجام دهد، اما برای احتیاط می‌توان اینجا نیز چک کرد
        instance = serializer.instance
        if hasattr(instance, 'owner'):
            if instance.owner != self.request.user:
                 logger.warning(f"Unauthorized attempt to update object {instance.id} by user {self.request.user.id}")
                 raise PermissionDenied("You do not own this object.")
        serializer.save()

    def perform_destroy(self, instance):
        """
        اطمینان از اینکه کاربر فقط می‌تواند شیء خود را حذف کند.
        """
        if hasattr(instance, 'owner'):
            if instance.owner != self.request.user:
                 logger.warning(f"Unauthorized attempt to delete object {instance.id} by user {self.request.user.id}")
                 raise PermissionDenied("You do not own this object.")
        instance.delete()

class SecureReadOnlyModelViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet پایه امن فقط برای خواندن برای مدل‌هایی که دارای فیلدهای زمان‌بندی هستند.
    """
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]

    def get_queryset(self):
        """
        اگر مدل دارای فیلد 'is_active' باشد، فقط آیتم‌های فعال را برمی‌گرداند.
        اگر مدل از BaseOwnedModel ارث می‌برد، فقط آیتم‌های متعلق به کاربر فعلی را برمی‌گرداند.
        """
        qs = super().get_queryset()

        if hasattr(qs.model, 'is_active'):
            qs = qs.filter(is_active=True)

        if hasattr(qs.model, 'owner'):
            user = self.request.user
            if not user.is_authenticated:
                return qs.none()
            qs = qs.filter(owner=user)

        return qs

# --- نماهای خاص برای مدل‌های Core ---

class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet فقط خواندنی برای لاگ‌های حسابرسی (Audit Logs).
    اجازه دسترسی فقط به کاربران احراز هویت شده.
    """
    queryset = AuditLog.objects.all().select_related('user') # select_related برای کارایی
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['user', 'action', 'target_model', 'created_at']
    ordering_fields = ['created_at']
    ordering = ['-created_at'] # جدیدترین اول

    def get_queryset(self):
        """
        کاربر فقط می‌تواند لاگ‌های خود را ببیند.
        ادمین می‌تواند همه را ببیند.
        """
        qs = super().get_queryset()
        user = self.request.user
        if not user.is_staff: # فقط ادمین می‌تواند همه را ببیند
            qs = qs.filter(user=user)
        return qs


class SystemSettingViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت تنظیمات سیستم.
    فقط کاربران ادمین می‌توانند تغییر دهند.
    """
    queryset = SystemSetting.objects.all()
    serializer_class = SystemSettingSerializer
    permission_classes = [permissions.IsAdminUser] # فقط ادمین
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['key', 'is_sensitive', 'data_type']

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def get_value(self, request):
        """
        اندپوینت برای گرفتن مقدار یک تنظیم خاص.
        اگر مقدار حساس باشد، مسک شده برگردانده می‌شود.
        """
        key = request.query_params.get('key', None)
        if not key:
            return Response({"error": "Key parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # فرض بر این است که مدل SystemSetting دارای متد get_parsed_value است
            setting = self.queryset.get(key__iexact=key)
            # سریالایزر مقدار را مسک می‌کند (اگر is_sensitive بود)
            serializer = self.get_serializer(setting)
            return Response(serializer.data)
        except SystemSetting.DoesNotExist:
            return Response({"error": "Setting not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching system setting {key}: {str(e)}")
            return Response({"error": "An error occurred while fetching the setting."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ممکن است نیاز به متد خاصی برای بروزرسانی داشته باشید که امنیت بیشتری داشته باشد
    # def update(self, request, *args, **kwargs):
    #     instance = self.get_object()
    #     if instance.is_sensitive and not request.user.is_staff:
    #         return Response({"error": "Only staff can modify sensitive settings."}, status=status.HTTP_403_FORBIDDEN)
    #     return super().update(request, *args, **kwargs)


class CacheEntryViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت ورودی‌های کش.
    فقط کاربران ادمین می‌توانند مدیریت کنند.
    """
    queryset = CacheEntry.objects.all()
    serializer_class = CacheEntrySerializer
    permission_classes = [permissions.IsAdminUser]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['key', 'expires_at', 'created_at']
    ordering_fields = ['created_at', 'expires_at']
    ordering = ['-created_at']

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def invalidate(self, request, pk=None):
        """
        اندپوینت برای باطل کردن (حذف) یک ورودی کش.
        """
        cache_entry = self.get_object()
        cache_entry.delete()
        return Response({"message": f"Cache entry '{cache_entry.key}' invalidated."}, status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAdminUser])
    def bulk_invalidate(self, request):
        """
        اندپوینت برای باطل کردن چندین ورودی کش با استفاده از کلیدهای موقوفه.
        """
        keys_to_invalidate = request.data.get('keys', [])
        if not isinstance(keys_to_invalidate, list):
             return Response({"error": "'keys' must be a list."}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count, _ = CacheEntry.objects.filter(key__in=keys_to_invalidate).delete()
        return Response({"message": f"Invalidated {deleted_count} cache entries."}, status=status.HTTP_200_OK)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAdminUser])
    def expired(self, request):
        """
        اندپوینت برای گرفتن ورودی‌های کش منقضی شده.
        """
        expired_entries = self.queryset.filter(expires_at__lt=timezone.now())
        serializer = self.get_serializer(expired_entries, many=True)
        return Response(serializer.data)

# --- نماهای عمومی ---
class SystemStatusView(APIView):
    """
    نمایی برای گزارش وضعیت کلی سیستم (Health, Uptime, Version, etc.).
    فقط برای کاربران ادمین.
    """
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        import platform
        from django.db import connection
        from django.conf import settings
        # اطلاعات سیستم
        status_info = {
            "status": "operational",
            "timestamp": timezone.now().isoformat(),
            "version": getattr(settings, 'SYSTEM_VERSION', 'unknown'),
            "uptime": "...", # می‌توانید از فایل یا متغیری برای ذخیره زمان شروع استفاده کنید
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "django_version": django.VERSION,
            "database": connection.vendor, # نوع پایگاه داده (PostgreSQL, SQLite, etc.)
            "settings_module": settings.SETTINGS_MODULE,
        }
        return Response(status_info)

# --- مثال: نمای تعامل با عامل (Agent Interaction) در MAS ---
class AgentInteractionView(APIView):
    """
    نمایی برای دریافت پیام‌ها یا رویدادهایی از سوی عامل‌های دیگر (مثل عامل‌های داده، معامله، ریسک).
    این می‌تواند یک نقطه پایانی (Endpoint) برای webhook یا ارسال پیام از طریق HTTP باشد.
    """
    permission_classes = [permissions.IsAuthenticated] # یا یک اجازه‌نامه سفارشی برای عامل‌ها (مثلاً IsAgentUser)

    def post(self, request):
        """
        پردازش پیام/رویداد دریافتی از یک عامل.
        """
        agent_id = request.data.get('agent_id') # شناسه عامل فرستنده
        event_type = request.data.get('event_type') # نوع رویداد (مثلاً: 'data_received', 'order_executed', 'risk_violation')
        payload = request.data.get('payload') # داده مربوطه

        if not agent_id or not event_type or payload is None:
            return Response({"error": "agent_id, event_type, and payload are required."}, status=status.HTTP_400_BAD_REQUEST)

        # منطق پردازش پیام
        try:
            # مثلاً فعال‌سازی یک تاسک Celery برای پردازش
            # from apps.core.tasks import process_agent_event_task
            # process_agent_event_task.delay(agent_id, event_type, payload)

            # یا ثبت در لاگ حسابرسی
            AuditLog.objects.create(
                user=request.user, # فرض: کاربر احراز هویت شده است (احتمالاً عامل)
                action=f"AGENT_EVENT_{event_type.upper()}",
                target_model="AgentInteraction",
                target_id=agent_id,
                details=payload,
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
            )
            logger.info(f"Agent event '{event_type}' received from agent {agent_id}.")

            return Response({"message": f"Event {event_type} from agent {agent_id} processed successfully."}, status=status.HTTP_202_ACCEPTED)
        except Exception as e:
            logger.error(f"Error processing agent event from {agent_id}: {str(e)}")
            return Response({"error": "Failed to process agent event."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- نماهای مرتبط با جستجو ---
class GlobalSearchView(APIView):
    """
    نمای جستجوی عمومی برای چندین مدل (مثلاً Instrument, Strategy, User).
    فقط برای کاربران احراز هویت شده.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        query = request.GET.get('q', '')
        if not query:
            return Response({"results": []}, status=status.HTTP_200_OK)

        results = []

        # جستجو در Instrument (اگر اپلیکیشن instruments وجود داشت)
        try:
            instruments = Instrument.objects.filter(
                Q(symbol__icontains=query) | Q(name__icontains=query),
                is_active=True
            )[:5] # محدود کردن نتایج
            for inst in instruments:
                 results.append({
                     'type': 'instrument',
                     'id': str(inst.id),
                     'name': str(inst),
                     'url': f'/instruments/{inst.id}/' # یا یک URL API
                 })
        except ImportError:
            pass # اگر اپلیکیشن وجود نداشت، نادیده گرفته می‌شود

        # جستجو در کاربران (اگر نیاز باشد و امن باشد)
        # try:
        #     users = CustomUser.objects.filter(
        #         Q(email__icontains=query) | Q(username_display__icontains=query)
        #     )[:5]
        #     for user in users:
        #         results.append({
        #             'type': 'user',
        #             'id': str(user.id),
        #             'name': user.email, # یا username_display
        #             'url': f'/users/{user.id}/'
        #         })
        # except:
        #     pass

        # جستجو در Exchange (اگر اپلیکیشن exchanges وجود داشت)
        try:
            exchanges = Exchange.objects.filter(
                Q(name__icontains=query) | Q(code__icontains=query),
                is_active=True
            )[:5]
            for exch in exchanges:
                 results.append({
                     'type': 'exchange',
                     'id': str(exch.id),
                     'name': str(exch),
                     'url': f'/exchanges/{exch.id}/'
                 })
        except ImportError:
            pass

        # جستجو در Strategy (اگر اپلیکیشن strategies وجود داشت)
        # try:
        #     from apps.strategies.models import Strategy
        #     strategies = Strategy.objects.filter(name__icontains=query, is_active=True)[:5]
        #     for strat in strategies:
        #          results.append({
        #              'type': 'strategy',
        #              'id': str(strat.id),
        #              'name': str(strat),
        #              'url': f'/strategies/{strat.id}/'
        #          })
        # except ImportError:
        #     pass

        # جستجو در TradingBot (اگر اپلیکیشن bots وجود داشت)
        # try:
        #     from apps.bots.models import TradingBot
        #     bots = TradingBot.objects.filter(name__icontains=query, is_active=True)[:5]
        #     for bot in bots:
        #          results.append({
        #              'type': 'bot',
        #              'id': str(bot.id),
        #              'name': str(bot),
        #              'url': f'/bots/{bot.id}/'
        #          })
        # except ImportError:
        #     pass

        # سایر مدل‌ها ...

        return Response({"results": results}, status=status.HTTP_200_OK)

logger.info("Core views loaded successfully.")
