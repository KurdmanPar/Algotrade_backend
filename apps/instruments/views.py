# apps/instruments/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from .models import (
    InstrumentGroup,
    InstrumentCategory,
    Instrument,
    InstrumentExchangeMap,
    IndicatorGroup,
    Indicator,
    IndicatorParameter,
    IndicatorTemplate,
    PriceActionPattern,
    SmartMoneyConcept,
    AIMetric,
    InstrumentWatchlist,
)
from .serializers import (
    InstrumentGroupSerializer,
    InstrumentCategorySerializer,
    InstrumentSerializer,
    InstrumentExchangeMapSerializer,
    IndicatorGroupSerializer,
    IndicatorSerializer,
    IndicatorParameterSerializer,
    IndicatorTemplateSerializer,
    PriceActionPatternSerializer,
    SmartMoneyConceptSerializer,
    AIMetricSerializer,
    InstrumentWatchlistSerializer,
)
from .permissions import IsOwnerOfWatchlist # فرض بر این است که این اجازه‌نامه وجود دارد
from .services import InstrumentService # فرض بر این است که این سرویس وجود دارد
from .exceptions import (
    InstrumentValidationError,
    InstrumentNotFound,
    InstrumentInactiveError,
    InstrumentDelistedError,
    IndicatorValidationError,
    PriceActionPatternError,
    SmartMoneyConceptError,
    AIMetricError,
    WatchlistError,
    WatchlistOwnershipError,
)
from apps.core.views import SecureModelViewSet # فرض بر این است که نماهای امن وجود دارد

# --- Instrument Group ViewSet ---
class InstrumentGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing InstrumentGroup model.
    Allows listing, creating, retrieving, updating, and deleting groups.
    """
    queryset = InstrumentGroup.objects.all()
    serializer_class = InstrumentGroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name'] # امکان فیلتر کردن لیست گروه‌ها بر اساس نام


# --- Instrument Category ViewSet ---
class InstrumentCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing InstrumentCategory model.
    Allows listing, creating, retrieving, updating, and deleting categories.
    """
    queryset = InstrumentCategory.objects.all()
    serializer_class = InstrumentCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name'] # امکان فیلتر کردن لیست دسته‌ها بر اساس نام


# --- Instrument ViewSet ---
class InstrumentViewSet(SecureModelViewSet): # استفاده از نماهای امن
    """
    ViewSet for managing Instrument model.
    Includes actions for filtering by group, category, symbol, and exchange.
    Utilizes InstrumentService for complex business logic.
    """
    serializer_class = InstrumentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'category', 'is_active', 'symbol', 'base_asset', 'quote_asset']

    def get_queryset(self):
        """
        Optionally filter instruments based on query parameters like 'search', 'active', 'exchange'.
        """
        queryset = Instrument.objects.all()

        # فیلتر بر اساس فعال/غیرفعال بودن
        is_active = self.request.query_params.get('is_active', None)
        if is_active is not None:
            is_active_bool = is_active.lower() in ['true', '1', 'yes']
            queryset = queryset.filter(is_active=is_active_bool)

        # جستجو در نماد یا نام
        search_query = self.request.query_params.get('search', None)
        if search_query:
            queryset = queryset.filter(
                Q(symbol__icontains=search_query) |
                Q(name__icontains=search_query)
            )

        # فیلتر بر اساس صرافی (نیازمند join با InstrumentExchangeMap)
        exchange_param = self.request.query_params.get('exchange', None)
        if exchange_param:
            # فرض بر این است که Instrument دارای یک رابطه معکوس به InstrumentExchangeMap به نام exchange_mappings است
            queryset = queryset.filter(exchange_mappings__exchange__name__iexact=exchange_param, exchange_mappings__is_active=True)

        # فیلتر بر اساس تاریخ راه‌اندازی (مثلاً بعد از یک تاریخ خاص)
        launched_after = self.request.query_params.get('launched_after', None)
        if launched_after:
            try:
                from django.utils.dateparse import parse_datetime
                dt = parse_datetime(launched_after)
                if dt:
                    queryset = queryset.filter(launch_date__gte=dt)
            except ValueError:
                pass # یا خطای مناسب صادر کنید

        return queryset.distinct() # distinct برای جلوگیری از نتایج تکراری در صورت join

    @action(detail=True, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def details(self, request, pk=None):
        """
        An extended detail view returning more comprehensive information about an instrument,
        potentially including exchange-specific mappings.
        """
        instrument = self.get_object() # اطمینان از اینکه شیء متعلق به کاربر فعلی نیست یا عمومی است
        # اینجا می‌توانید منطق بیشتری اضافه کنید، مثلاً گرفتن اطلاعات از سرویس داده بازار
        serializer = self.get_serializer(instrument)
        # مثال: افزودن اطلاعات صرافی مرتبط به خروجی
        exchange_maps = instrument.exchange_mappings.filter(is_active=True).select_related('exchange')
        exchange_info = [
            {
                'exchange_name': em.exchange.name,
                'exchange_symbol': em.exchange_symbol,
                'tick_size': em.tick_size,
                'lot_size': em.lot_size,
                'min_notional': em.min_notional,
            }
            for em in exchange_maps
        ]
        data = serializer.data
        data['exchange_details'] = exchange_info
        return Response(data)

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def active(self, request):
        """
        Returns only active instruments.
        """
        active_instruments = self.get_queryset().filter(is_active=True)
        serializer = self.get_serializer(active_instruments, many=True)
        return Response(serializer.data)

    # می‌توانید اکشن‌های دیگری مانند 'by_group', 'by_exchange' را نیز اضافه کنید.


# --- Instrument Exchange Map ViewSet ---
class InstrumentExchangeMapViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing InstrumentExchangeMap model.
    Allows CRUD operations on instrument-exchange mappings.
    """
    queryset = InstrumentExchangeMap.objects.all()
    serializer_class = InstrumentExchangeMapSerializer
    permission_classes = [IsAuthenticated] # احراز هویت برای مدیریت نگاشت‌ها ضروری است
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exchange', 'instrument', 'is_active']

    def get_queryset(self):
        # ممکن است بخواهید فقط نگاشت‌های فعال را پیش‌فرض برگردانید
        return InstrumentExchangeMap.objects.filter(is_active=True)


# --- Indicator Group ViewSet ---
class IndicatorGroupViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing IndicatorGroup model.
    """
    queryset = IndicatorGroup.objects.all()
    serializer_class = IndicatorGroupSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['name']


# --- Indicator ViewSet ---
class IndicatorViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Indicator model.
    Includes actions for getting active/builtin indicators.
    """
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['group', 'is_active', 'is_builtin', 'code']

    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticatedOrReadOnly])
    def active_builtin(self, request):
        """
        Returns only active built-in indicators.
        """
        active_builtin_indicators = self.queryset.filter(is_active=True, is_builtin=True)
        serializer = self.get_serializer(active_builtin_indicators, many=True)
        return Response(serializer.data)


# --- Indicator Parameter ViewSet ---
class IndicatorParameterViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet for reading IndicatorParameter model.
    Creation/Updates are typically managed by system admins or during indicator definition.
    """
    queryset = IndicatorParameter.objects.all()
    serializer_class = IndicatorParameterSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['indicator']


# --- Indicator Template ViewSet ---
class IndicatorTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing IndicatorTemplate model.
    Could be restricted to authenticated users or owners depending on use case.
    """
    queryset = IndicatorTemplate.objects.all()
    serializer_class = IndicatorTemplateSerializer
    permission_classes = [IsAuthenticatedOrReadOnly] # یا اجازه‌نامه سفارشی برای مالکیت
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['indicator', 'is_active']

    def get_permissions(self):
        """
        Instantiates and returns the list of permissions that this view requires.
        Restricts creation/listing for non-admins if needed.
        """
        permission_classes = []
        if self.action in ["create", "update", "partial_update", "destroy"]:
            permission_classes = [IsAuthenticated] # فقط کاربران احراز هویت شده بتوانند تغییر دهند
            # یا اضافه کردن اجازه‌نامه‌ای مانند IsAdminUser یا IsOwnerOfTemplate
        else:
            permission_classes = [IsAuthenticatedOrReadOnly] # برای خواندن، می‌تواند عمومی باشد یا فقط احراز هویت شده
        return [permission() for permission in permission_classes]


# --- Price Action Pattern ViewSet ---
class PriceActionPatternViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing PriceActionPattern model.
    """
    queryset = PriceActionPattern.objects.all()
    serializer_class = PriceActionPatternSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'code']


# --- Smart Money Concept ViewSet ---
class SmartMoneyConceptViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing SmartMoneyConcept model.
    """
    queryset = SmartMoneyConcept.objects.all()
    serializer_class = SmartMoneyConceptSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'code']


# --- AI Metric ViewSet ---
class AIMetricViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing AIMetric model.
    """
    queryset = AIMetric.objects.all()
    serializer_class = AIMetricSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_active', 'data_type', 'code']


# --- Instrument Watchlist ViewSet ---
class InstrumentWatchlistViewSet(SecureModelViewSet): # استفاده از نماهای امن
    """
    ViewSet for managing InstrumentWatchlist model.
    Restricted to authenticated users, with ownership checks.
    """
    serializer_class = InstrumentWatchlistSerializer
    permission_classes = [IsAuthenticated, IsOwnerOfWatchlist] # بررسی مالکیت در هر عملیات شیء
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['is_public'] # فیلتر بر اساس عمومی یا خصوصی بودن

    def get_queryset(self):
        """
        Returns watchlists owned by the current user, or public ones if requested.
        """
        user = self.request.user
        # فقط نمایش لیست‌های مالک خود یا لیست‌های عمومی
        return InstrumentWatchlist.objects.filter(
            Q(owner=user) | Q(is_public=True)
        )

    def perform_create(self, serializer):
        """
        Sets the owner of the new watchlist to the current user.
        """
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOfWatchlist])
    def add_instrument(self, request, pk=None):
        """
        Adds an instrument to a specific watchlist (requires ownership).
        """
        watchlist = self.get_object() # این از اجازه‌نامه IsOwnerOfWatchlist استفاده می‌کند
        instrument_id = request.data.get('instrument_id')
        if not instrument_id:
            return Response({"error": "instrument_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .models import Instrument # ایمپورت درون تابع برای جلوگیری از حلقه
            instrument = Instrument.objects.get(id=instrument_id)
            # استفاده از add برای M2M
            watchlist.instruments.add(instrument)
            return Response({"message": f"Added {instrument.symbol} to {watchlist.name}."}, status=status.HTTP_200_OK)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred adding the instrument."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated, IsOwnerOfWatchlist])
    def remove_instrument(self, request, pk=None):
        """
        Removes an instrument from a specific watchlist (requires ownership).
        """
        watchlist = self.get_object()
        instrument_id = request.data.get('instrument_id')
        if not instrument_id:
            return Response({"error": "instrument_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from .models import Instrument
            instrument = Instrument.objects.get(id=instrument_id)
            watchlist.instruments.remove(instrument)
            return Response({"message": f"Removed {instrument.symbol} from {watchlist.name}."}, status=status.HTTP_200_OK)
        except Instrument.DoesNotExist:
            return Response({"error": "Instrument not found."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred removing the instrument."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
