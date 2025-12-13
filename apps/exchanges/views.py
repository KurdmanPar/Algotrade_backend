# apps/exchanges/views.py

from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Q
from .models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    OrderHistory,
    MarketDataCandle,
)
from .serializers import (
    ExchangeSerializer,
    ExchangeAccountSerializer,
    WalletSerializer,
    WalletBalanceSerializer,
    AggregatedPortfolioSerializer,
    AggregatedAssetPositionSerializer,
    OrderHistorySerializer,
    MarketDataCandleSerializer,
)
from .services import ExchangeService, MarketDataService # فرض بر این است که این سرویس‌ها وجود دارند
from .permissions import IsOwnerOfExchangeAccount, IsOwnerOfRelatedObject # فرض بر این است که این اجازه‌نامه‌ها وجود دارند
from .exceptions import ExchangeSyncError, DataFetchError, OrderExecutionError # فرض بر این است که این استثناها وجود دارند
from apps.core.views import SecureModelViewSet # فرض بر این است که این نما وجود دارد
from apps.core.permissions import IsOwnerOrReadOnly, IsAdminUserOrReadOnly # از core استفاده می‌کنیم
from apps.core.exceptions import SecurityException # از core استفاده می‌کنیم
from apps.core.helpers import get_client_ip # از core استفاده می‌کنیم
from apps.core.tasks import log_audit_event_task # از core استفاده می‌کنیم
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد
from apps.bots.models import TradingBot # فرض بر این است که مدل بات وجود دارد
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

# --- نماهای عمومی (Public Views) ---
class HealthCheckView(generics.GenericAPIView):
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

class PingView(generics.GenericAPIView):
    """
    نمای ساده برای پینگ کردن سرور.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        client_ip = get_client_ip(request)
        return Response({"pong": timezone.now(), "client_ip": client_ip}, status=status.HTTP_200_OK)


# --- نماهای اصلی (Main Views) ---

class ExchangeViewSet(viewsets.ReadOnlyModelViewSet): # فقط خواندنی برای عموم
    """
    ViewSet فقط خواندنی برای نمادها.
    """
    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # یا فقط IsAuthenticated اگر محرمانه است
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['type', 'is_active', 'is_sandbox', 'code'] # امکان فیلتر کردن


class ExchangeAccountViewSet(SecureModelViewSet): # ارث از SecureModelViewSet از core
    """
    ViewSet برای مدیریت حساب‌های صرافی.
    شامل اکشن‌هایی برای همگام‌سازی داده و لینک کردن بات‌ها.
    """
    serializer_class = ExchangeAccountSerializer
    # permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # استفاده از SecureModelViewSet
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exchange', 'is_active', 'is_paper_trading', 'owner'] # owner از BaseOwnedModel (core)

    def get_queryset(self):
        """
        کاربر فقط می‌تواند حساب‌های خود را ببیند.
        این منطق در SecureModelViewSet (که از BaseOwnedModelManager ارث می‌برد) اعمال می‌شود.
        """
        # فقط اگر نیاز به فیلترهای بیشتری داشتید
        user = self.request.user
        if not user.is_authenticated:
            return ExchangeAccount.objects.none()
        # این فیلتر توسط SecureModelViewSet یا OwnerFilterMixin در core انجام می‌شود
        # return ExchangeAccount.objects.filter(owner=user) # این در SecureModelViewSet انجام می‌شود
        return ExchangeAccount.objects.all() # فقط اگر نیاز به دیدن همه برای ادمین یا نقش خاصی داشتید

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfExchangeAccount])
    def sync_account_data(self, request, pk=None):
        """
        همگام‌سازی موجودی، سفارشات و سایر داده‌های حساب از صرافی.
        """
        account = self.get_object() # این از اجازه‌نامه IsOwnerOfExchangeAccount (یا IsOwnerOrReadOnly) استفاده می‌کند
        try:
            # استفاده از سرویس برای انجام عملیات پیچیده
            updated_info = ExchangeService.sync_exchange_account(account)
            # به‌روزرسانی مدل
            account.account_info = updated_info.get('account_info', {})
            account.last_sync_at = timezone.now()
            account.save(update_fields=['account_info', 'last_sync_at'])

            # احتمالاً باید موجودی‌ها و سفارش‌ها را نیز به‌روزرسانی کنید
            # این بخش بستگی به نحوه پیاده‌سازی سرویس دارد
            # ExchangeService.update_balances(account, updated_info.get('balances', []))
            # ExchangeService.update_orders(account, updated_info.get('orders', []))

            # ثبت لاگ حسابرسی
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='ACCOUNT_SYNC_SUCCESS',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'sync_time': account.last_sync_at.isoformat()},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )

            return Response({"message": f"Account {account.label} synced successfully", "sync_time": account.last_sync_at})
        except ExchangeSyncError as e:
            # ثبت خطا در حسابرسی
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='ACCOUNT_SYNC_ERROR',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'error': str(e)},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Error syncing account {account.id} for user {account.owner.email}: {str(e)}")
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='ACCOUNT_SYNC_ERROR_UNEXPECTED',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'error': str(e)},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"error": "An unexpected error occurred during sync."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfExchangeAccount])
    def link_bot(self, request, pk=None):
        """
        لینک کردن یک TradingBot به این حساب صرافی.
        """
        account = self.get_object()
        bot_id = request.data.get('bot_id')
        if not bot_id:
            return Response({"error": "bot_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.bots.models import TradingBot # import درون تابع برای جلوگیری از حلقه
            bot = TradingBot.objects.get(id=bot_id, owner=account.owner) # اطمینان از مالکیت بات - تغییر: owner به جای user
            account.linked_bots.add(bot)
            account.save()
            logger.info(f"Bot {bot.name} linked to account {account.label} by user {account.owner.email}.")
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='BOT_LINKED_TO_ACCOUNT',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'bot_id': bot.id, 'bot_name': bot.name},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"message": f"Bot {bot.name} linked to account {account.label}."})
        except TradingBot.DoesNotExist:
            logger.warning(f"Attempt to link non-existent or non-owned bot {bot_id} to account {account.label} by user {account.owner.email}.")
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='BOT_LINK_ERROR',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'error': 'Bot not found or you do not own it.', 'attempted_bot_id': bot_id},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            raise PermissionDenied("Bot not found or you do not own it.")
        except Exception as e:
            logger.error(f"Error linking bot {bot_id} to account {account.id}: {str(e)}")
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='BOT_LINK_ERROR_UNEXPECTED',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'error': str(e)},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"error": "An error occurred linking the bot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfExchangeAccount])
    def unlink_bot(self, request, pk=None):
        """
        لغو لینک یک TradingBot از این حساب صرافی.
        """
        account = self.get_object()
        bot_id = request.data.get('bot_id')
        if not bot_id:
            return Response({"error": "bot_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.bots.models import TradingBot
            bot = TradingBot.objects.get(id=bot_id, owner=account.owner) # اطمینان از مالکیت بات - تغییر: owner به جای user
            account.linked_bots.remove(bot)
            account.save()
            logger.info(f"Bot {bot.name} unlinked from account {account.label} by user {account.owner.email}.")
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='BOT_UNLINKED_FROM_ACCOUNT',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'bot_id': bot.id, 'bot_name': bot.name},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"message": f"Bot {bot.name} unlinked from account {account.label}."})
        except TradingBot.DoesNotExist:
            logger.warning(f"Attempt to unlink non-existent or non-owned bot {bot_id} from account {account.label} by user {account.owner.email}.")
            raise PermissionDenied("Bot not found or you do not own it.")
        except Exception as e:
            logger.error(f"Error unlinking bot {bot_id} from account {account.id}: {str(e)}")
            log_audit_event_task.delay(
                user_id=account.owner.id,
                action='BOT_UNLINK_ERROR',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={'error': str(e)},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"error": "An error occurred unlinking the bot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت کیف پول‌ها.
    """
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # باید مالک حساب صرافی مربوطه باشد - از core
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exchange_account', 'wallet_type', 'is_default', 'is_margin_enabled'] # فیلتر بر اساس حساب و نوع

    def get_queryset(self):
        """
        کاربر فقط می‌تواند کیف پول‌های مربوط به حساب‌های خود را ببیند.
        """
        user = self.request.user
        if not user.is_authenticated:
            return Wallet.objects.none()
        # فیلتر بر اساس مالک حساب صرافی که کیف پول متعلق به آن است
        return Wallet.objects.filter(exchange_account__owner=user) # تغییر: owner به جای user


class WalletBalanceViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet فقط خواندنی برای موجودی‌های کیف پول.
    """
    queryset = WalletBalance.objects.all()
    serializer_class = WalletBalanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # باید مالک حساب صرافی مربوطه باشد - از core
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['wallet', 'asset_symbol'] # فیلتر بر اساس کیف پول و نماد

    def get_queryset(self):
        """
        کاربر فقط می‌تواند موجودی‌های مربوط به حساب‌های خود را ببیند.
        """
        user = self.request.user
        if not user.is_authenticated:
            return WalletBalance.objects.none()
        # فیلتر بر اساس مالک حساب صرافی که کیف پول و موجودی متعلق به آن است
        return WalletBalance.objects.filter(wallet__exchange_account__owner=user) # تغییر: owner به جای user


class AggregatedPortfolioViewSet(SecureModelViewSet): # ارث از SecureModelViewSet از core
    """
    ViewSet برای مدیریت پرتفوی تجمیعی.
    فقط مالک می‌تواند دسترسی داشته باشد.
    """
    serializer_class = AggregatedPortfolioSerializer
    # permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly] # استفاده از SecureModelViewSet
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['base_currency', 'owner'] # owner از BaseOwnedModel (core)

    def get_queryset(self):
        """
        فقط پرتفوی کاربر فعلی.
        """
        user = self.request.user
        if not user.is_authenticated:
            return AggregatedPortfolio.objects.none()
        # این فیلتر توسط SecureModelViewSet انجام می‌شود
        # return AggregatedPortfolio.objects.filter(owner=user)
        return AggregatedPortfolio.objects.all() # فقط اگر نیاز به دیدن همه برای ادمین یا نقش خاصی داشتید

    def perform_create(self, serializer):
        """
        اطمینان از اینکه کاربر فقط یک پرتفوی داشته باشد.
        """
        user = self.request.user
        if AggregatedPortfolio.objects.filter(owner=user).exists(): # تغییر: owner به جای user
            raise ValidationError("Portfolio already exists for this user.")
        # owner از SecureModelViewSet یا OwnerUpdateMixin در core تنظیم می‌شود
        serializer.save() # owner در SecureModelViewSet تنظیم می‌شود


class AggregatedAssetPositionViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet فقط خواندنی برای پوزیشن‌های تجمیعی دارایی.
    فقط مالک پرتفوی می‌تواند دسترسی داشته باشد.
    """
    serializer_class = AggregatedAssetPositionSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfRelatedObject] # از core
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['aggregated_portfolio', 'asset_symbol'] # فیلتر بر اساس پرتفوی و نماد

    def get_queryset(self):
        """
        فقط پوزیشن‌های مربوط به پرتفوی کاربر فعلی.
        """
        user = self.request.user
        if not user.is_authenticated:
            return AggregatedAssetPosition.objects.none()
        # فیلتر بر اساس مالک پرتفوی
        return AggregatedAssetPosition.objects.filter(aggregated_portfolio__owner=user) # تغییر: owner به جای user


class OrderHistoryViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    """
    ViewSet فقط خواندنی برای تاریخچه سفارشات.
    فقط مالک حساب صرافی مربوطه می‌تواند دسترسی داشته باشد.
    """
    serializer_class = OrderHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfRelatedObject] # باید مالک حساب صرافی مربوطه باشد - از core
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exchange_account', 'symbol', 'status', 'side', 'order_type', 'time_placed'] # فیلترهای زیاد
    ordering_fields = ['time_placed', 'time_updated']
    ordering = ['-time_placed'] # جدیدترین اول

    def get_queryset(self):
        """
        کاربر فقط می‌تواند تاریخچه سفارشات مربوط به حساب‌های خود را ببیند.
        """
        user = self.request.user
        if not user.is_authenticated:
            return OrderHistory.objects.none()
        # فیلتر بر اساس مالک حساب صرافی که سفارش مربوط به آن است
        return OrderHistory.objects.filter(exchange_account__owner=user) # تغییر: owner به جای user


class MarketDataCandleViewSet(viewsets.ReadOnlyModelViewSet): # فقط خواندنی
    """
    ViewSet فقط خواندنی برای داده‌های کندل بازار.
    """
    serializer_class = MarketDataCandleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # یا فقط IsAuthenticated - بسته به نیاز
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['exchange', 'symbol', 'interval', 'open_time'] # فیلترهای زیاد
    ordering_fields = ['open_time']
    ordering = ['-open_time'] # جدیدترین اول

    def get_queryset(self):
        """
        امکان فیلتر کردن بر اساس exchange، symbol، interval.
        """
        queryset = MarketDataCandle.objects.all()
        exchange_code = self.request.query_params.get('exchange', None)
        symbol = self.request.query_params.get('symbol', None)
        interval = self.request.query_params.get('interval', None)

        if exchange_code:
            queryset = queryset.filter(exchange__code__iexact=exchange_code)
        if symbol:
            queryset = queryset.filter(symbol__iexact=symbol)
        if interval:
            queryset = queryset.filter(interval__iexact=interval)

        return queryset

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def latest(self, request):
        """
        برمی‌گرداند آخرین کندل برای یک نماد و بازه زمانی مشخص.
        """
        symbol = request.query_params.get('symbol', None)
        interval = request.query_params.get('interval', None)
        if not symbol or not interval:
            return Response({"error": "symbol and interval are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            latest_candle = MarketDataCandle.objects.filter(
                symbol__iexact=symbol,
                interval__iexact=interval
            ).latest('open_time')

            serializer = self.get_serializer(latest_candle)
            return Response(serializer.data)
        except MarketDataCandle.DoesNotExist:
            return Response({"message": "No candle found for the given symbol and interval."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching latest candle for {symbol} ({interval}): {str(e)}")
            log_audit_event_task.delay(
                user_id=getattr(request.user, 'id', None), # اگر احراز هویت نشده باشد، None
                action='FETCH_LATEST_CANDLE_ERROR',
                target_model_name='MarketDataCandle',
                target_id=None, # چون نمی‌دانیم شناسه چیست
                details={'error': str(e), 'symbol': symbol, 'interval': interval},
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            return Response({"error": "An error occurred fetching the latest candle."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# --- نماهای دیگر ---
# می‌توانید نماهایی برای مدل‌های دیگری که در instruments تعریف می‌کنید (مثل PriceActionPattern، SmartMoneyConcept، AIMetric) نیز اضافه کنید
# مثلاً:
# class PriceActionPatternViewSet(viewsets.ReadOnlyModelViewSet):
#     queryset = PriceActionPattern.objects.all()
#     serializer_class = PriceActionPatternSerializer
#     permission_classes = [permissions.IsAuthenticatedOrReadOnly]
#     filter_backends = [DjangoFilterBackend]
#     filterset_fields = ['name', 'code', 'is_active']

logger.info("Exchanges views loaded successfully.")
