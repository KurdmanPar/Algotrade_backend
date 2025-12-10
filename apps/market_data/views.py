# apps/market_data/views.py

from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Q
from .models import (
    DataSource,
    MarketDataConfig,
    MarketDataSnapshot,
    MarketDataOrderBook,
    MarketDataTick,
    MarketDataSyncLog,
    MarketDataCache,
)
from .serializers import (
    DataSourceSerializer,
    MarketDataConfigSerializer,
    MarketDataSnapshotSerializer,
    MarketDataOrderBookSerializer,
    MarketDataTickSerializer,
    MarketDataSyncLogSerializer,
    MarketDataCacheSerializer,
)
from .services import MarketDataService # فرض بر این است که این سرویس وجود دارد
from .permissions import IsOwnerOfMarketDataConfig, HasReadAccessToDataSource # فرض بر این است که این اجازه‌نامه‌ها وجود دارند
from .exceptions import DataSyncError, DataFetchError # فرض بر این است که این استثناها وجود دارند
from apps.core.views import SecureModelViewSet # فرض بر این است که این نما وجود دارد
from apps.agents.models import Agent # فرض بر این است که مدل Agent وجود دارد (برای اتصال به عامل داده)

# --- نماهای DataSource ---
class DataSourceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing DataSource model.
    """
    queryset = DataSource.objects.all()
    serializer_class = DataSourceSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # یا فقط IsAuthenticated
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type', 'is_active', 'is_sandbox']


# --- نماهای MarketDataConfig ---
class MarketDataConfigViewSet(SecureModelViewSet):
    """
    ViewSet for managing MarketDataConfig model.
    Includes actions for subscribing/unsubscribing agents and triggering syncs.
    """
    serializer_class = MarketDataConfigSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfMarketDataConfig]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['instrument__symbol', 'data_source__name', 'timeframe', 'data_type', 'is_realtime', 'is_historical', 'status']

    def get_queryset(self):
        # کاربر فقط می‌تواند کانفیگ‌های خود را ببیند (اگر از SecureModelViewSet ارث برده باشد)
        # در غیر این صورت، اینجا باید فیلتر شود
        # return MarketDataConfig.objects.filter(instrument__owner=self.request.user) # مثال فرضی owner در Instrument
        return MarketDataConfig.objects.all() # تا زمانی که owner تعریف شود

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfMarketDataConfig])
    def trigger_sync(self, request, pk=None):
        """
        Triggers a historical data sync for this config.
        """
        config = self.get_object()
        try:
            # استفاده از سرویس برای شروع همگام‌سازی
            sync_log = MarketDataService.trigger_historical_sync(config)
            serializer = MarketDataSyncLogSerializer(sync_log)
            return Response(serializer.data, status=status.HTTP_202_ACCEPTED)
        except DataSyncError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred during sync trigger."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfMarketDataConfig])
    def subscribe_agent(self, request, pk=None):
        """
        Subscribes a specific data collection agent to this config.
        """
        config = self.get_object()
        agent_id = request.data.get('agent_id')
        if not agent_id:
            return Response({"error": "agent_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.agents.models import Agent # ایمپورت داخل تابع برای جلوگیری از حلقه
            agent = Agent.objects.get(id=agent_id, owner=self.request.user) # اطمینان از مالکیت عامل
            # منطق اتصال عامل به کانفیگ (مثلاً ذخیره در یک مدل میانی یا به‌روزرسانی فیلد status)
            config.status = 'SUBSCRIBED'
            config.save(update_fields=['status'])
            # همچنین می‌توانید یک رابطه ManyToMany ایجاد کنید یا یک مدل جدید مثل AgentSubscription
            # agent.subscribed_configs.add(config)
            return Response({"message": f"Agent {agent.name} subscribed to config for {config.instrument.symbol}."})
        except Agent.DoesNotExist:
            return Response({"error": "Agent not found or you do not own it."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred subscribing the agent."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfMarketDataConfig])
    def unsubscribe_agent(self, request, pk=None):
        """
        Unsubscribes a specific data collection agent from this config.
        """
        config = self.get_object()
        agent_id = request.data.get('agent_id')
        if not agent_id:
            return Response({"error": "agent_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.agents.models import Agent
            agent = Agent.objects.get(id=agent_id, owner=self.request.user)
            config.status = 'UNSUBSCRIBED'
            config.save(update_fields=['status'])
            # agent.subscribed_configs.remove(config)
            return Response({"message": f"Agent {agent.name} unsubscribed from config for {config.instrument.symbol}."})
        except Agent.DoesNotExist:
            return Response({"error": "Agent not found or you do not own it."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred unsubscribing the agent."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- نماهای MarketDataSnapshot ---
class MarketDataSnapshotViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet for retrieving MarketDataSnapshot data.
    Supports filtering by instrument, time range, and config.
    """
    serializer_class = MarketDataSnapshotSerializer
    permission_classes = [permissions.IsAuthenticated] # یا فقط IsAuthenticatedOrReadOnly
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config__instrument__symbol', 'config__data_source__name', 'config__timeframe', 'config__data_type']

    def get_queryset(self):
        queryset = MarketDataSnapshot.objects.all()
        # فیلتر بر اساس بازه زمانی
        start_time = self.request.query_params.get('start_time', None)
        end_time = self.request.query_params.get('end_time', None)
        if start_time:
            try:
                start_dt = timezone.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass # یا یک استثنا ب throws کنید
        if end_time:
            try:
                end_dt = timezone.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_dt)
            except ValueError:
                pass

        # فیلتر بر اساس config (اگر ID داده شود)
        config_id = self.request.query_params.get('config_id', None)
        if config_id:
            queryset = queryset.filter(config_id=config_id)

        # فیلتر بر اساس instrument (اگر ID داده شود)
        instrument_id = self.request.query_params.get('instrument_id', None)
        if instrument_id:
            queryset = queryset.filter(config__instrument_id=instrument_id)

        # مرتب سازی پیش‌فرض بر اساس زمان (جدیدترین اول)
        return queryset.order_by('-timestamp')

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def latest(self, request):
        """
        Returns the latest snapshot for a given instrument and timeframe.
        """
        instrument_symbol = request.query_params.get('instrument', None)
        timeframe = request.query_params.get('timeframe', None)
        if not instrument_symbol or not timeframe:
            return Response({"error": "instrument and timeframe are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latest_snapshot = MarketDataSnapshot.objects.filter(
                config__instrument__symbol__iexact=instrument_symbol,
                config__timeframe__iexact=timeframe
            ).latest('timestamp')

            serializer = self.get_serializer(latest_snapshot)
            return Response(serializer.data)
        except MarketDataSnapshot.DoesNotExist:
            return Response({"message": "No snapshot found for the given instrument and timeframe."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred fetching the latest snapshot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- نماهای MarketDataOrderBook ---
class MarketDataOrderBookViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet for retrieving MarketDataOrderBook data.
    Supports filtering by instrument and time range.
    """
    serializer_class = MarketDataOrderBookSerializer
    permission_classes = [permissions.IsAuthenticated] # یا فقط IsAuthenticatedOrReadOnly
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config__instrument__symbol', 'config__data_source__name']

    def get_queryset(self):
        queryset = MarketDataOrderBook.objects.all()
        start_time = self.request.query_params.get('start_time', None)
        end_time = self.request.query_params.get('end_time', None)
        if start_time:
            try:
                start_dt = timezone.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass
        if end_time:
            try:
                end_dt = timezone.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_dt)
            except ValueError:
                pass

        config_id = self.request.query_params.get('config_id', None)
        if config_id:
            queryset = queryset.filter(config_id=config_id)

        instrument_id = self.request.query_params.get('instrument_id', None)
        if instrument_id:
            queryset = queryset.filter(config__instrument_id=instrument_id)

        return queryset.order_by('-timestamp') # جدیدترین اول

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def latest(self, request):
        """
        Returns the latest order book for a given instrument.
        """
        instrument_symbol = request.query_params.get('instrument', None)
        if not instrument_symbol:
            return Response({"error": "instrument is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latest_book = MarketDataOrderBook.objects.filter(
                config__instrument__symbol__iexact=instrument_symbol,
            ).latest('timestamp')

            serializer = self.get_serializer(latest_book)
            return Response(serializer.data)
        except MarketDataOrderBook.DoesNotExist:
            return Response({"message": "No order book found for the given instrument."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred fetching the latest order book."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- نماهای MarketDataTick ---
class MarketDataTickViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet for retrieving MarketDataTick data.
    Supports filtering by instrument, time range, and side.
    """
    serializer_class = MarketDataTickSerializer
    permission_classes = [permissions.IsAuthenticated] # یا فقط IsAuthenticatedOrReadOnly
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config__instrument__symbol', 'config__data_source__name', 'side']

    def get_queryset(self):
        queryset = MarketDataTick.objects.all()
        start_time = self.request.query_params.get('start_time', None)
        end_time = self.request.query_params.get('end_time', None)
        if start_time:
            try:
                start_dt = timezone.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__gte=start_dt)
            except ValueError:
                pass
        if end_time:
            try:
                end_dt = timezone.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(timestamp__lte=end_dt)
            except ValueError:
                pass

        config_id = self.request.query_params.get('config_id', None)
        if config_id:
            queryset = queryset.filter(config_id=config_id)

        instrument_id = self.request.query_params.get('instrument_id', None)
        if instrument_id:
            queryset = queryset.filter(config__instrument_id=instrument_id)

        return queryset.order_by('-timestamp') # جدیدترین اول


# --- نماهای MarketDataSyncLog ---
class MarketDataSyncLogViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet for retrieving MarketDataSyncLog entries.
    Supports filtering by config, status, and time range.
    """
    serializer_class = MarketDataSyncLogSerializer
    permission_classes = [permissions.IsAuthenticated] # یا فقط IsAuthenticatedOrReadOnly
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config__instrument__symbol', 'config__data_source__name', 'status']

    def get_queryset(self):
        queryset = MarketDataSyncLog.objects.all()
        start_time = self.request.query_params.get('start_time', None)
        end_time = self.request.query_params.get('end_time', None)
        if start_time:
            try:
                start_dt = timezone.datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                queryset = queryset.filter(start_time__gte=start_dt)
            except ValueError:
                pass
        if end_time:
            try:
                end_dt = timezone.datetime.fromisoformat(end_time.replace('Z', '+00:00'))
                queryset = queryset.filter(end_time__lte=end_dt)
            except ValueError:
                pass

        config_id = self.request.query_params.get('config_id', None)
        if config_id:
            queryset = queryset.filter(config_id=config_id)

        return queryset.order_by('-start_time') # جدیدترین اول


# --- نماهای MarketDataCache ---
class MarketDataCacheViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet for retrieving cached MarketData entries.
    """
    serializer_class = MarketDataCacheSerializer
    permission_classes = [permissions.IsAuthenticated] # یا فقط IsAuthenticatedOrReadOnly
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['config__instrument__symbol', 'config__data_source__name']

    def get_queryset(self):
        # فقط کش‌های مربوط به کانفیگ‌های قابل دسترسی کاربر فعلی (یا عمومی)
        # فرض بر این است که دسترسی به کانفیگ معادل دسترسی به کش است
        # این بستگی به نحوه تعریف دسترسی دارد
        queryset = MarketDataCache.objects.all()
        config_id = self.request.query_params.get('config_id', None)
        if config_id:
            queryset = queryset.filter(config_id=config_id)

        instrument_id = self.request.query_params.get('instrument_id', None)
        if instrument_id:
            queryset = queryset.filter(config__instrument_id=instrument_id)

        return queryset.order_by('-cached_at') # جدیدترین کش اول
