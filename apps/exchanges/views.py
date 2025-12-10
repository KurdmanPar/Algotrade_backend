# apps/exchanges/views.py

from rest_framework import viewsets, permissions, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
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
from .permissions import IsOwnerOfExchangeAccount # فرض بر این است که این اجازه‌نامه وجود دارد
from .exceptions import ExchangeSyncError, DataFetchError # فرض بر این است که این استثناها وجود دارند
from apps.core.views import SecureModelViewSet # فرض بر این است که این نما وجود دارد

User = get_user_model()

class ExchangeViewSet(viewsets.ReadOnlyModelViewSet): # فقط خواندنی برای عموم
    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # یا فقط IsAuthenticated اگر محرمانه است


class ExchangeAccountViewSet(SecureModelViewSet):
    """
    ViewSet for managing Exchange Accounts.
    Includes actions for syncing account data and linking bots.
    """
    serializer_class = ExchangeAccountSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfExchangeAccount]

    def get_queryset(self):
        # کاربر فقط می‌تواند حساب‌های خود را ببیند
        return ExchangeAccount.objects.filter(user=self.request.user)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfExchangeAccount])
    def sync_account_data(self, request, pk=None):
        """
        Syncs balance, orders, and other account data from the exchange.
        """
        account = self.get_object() # این از اجازه‌نامه IsOwnerOfExchangeAccount استفاده می‌کند
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

            return Response({"message": f"Account {account.label} synced successfully", "sync_time": account.last_sync_at})
        except ExchangeSyncError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred during sync."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfExchangeAccount])
    def link_bot(self, request, pk=None):
        """
        Links a TradingBot to this ExchangeAccount.
        """
        account = self.get_object()
        bot_id = request.data.get('bot_id')
        if not bot_id:
            return Response({"error": "bot_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.bots.models import TradingBot # ایمپورت درون تابع برای جلوگیری از حلقه
            bot = TradingBot.objects.get(id=bot_id, owner=account.user) # اطمینان از مالکیت بات
            account.linked_bots.add(bot)
            account.save()
            return Response({"message": f"Bot {bot.name} linked to account {account.label}."})
        except TradingBot.DoesNotExist:
            raise PermissionDenied("Bot not found or you do not own it.")
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred linking the bot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOwnerOfExchangeAccount])
    def unlink_bot(self, request, pk=None):
        """
        Unlinks a TradingBot from this ExchangeAccount.
        """
        account = self.get_object()
        bot_id = request.data.get('bot_id')
        if not bot_id:
            return Response({"error": "bot_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            from apps.bots.models import TradingBot
            bot = TradingBot.objects.get(id=bot_id, owner=account.user)
            account.linked_bots.remove(bot)
            account.save()
            return Response({"message": f"Bot {bot.name} unlinked from account {account.label}."})
        except TradingBot.DoesNotExist:
            raise PermissionDenied("Bot not found or you do not own it.")
        except Exception as e:
            # لاگ کنید
            return Response({"error": "An error occurred unlinking the bot."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    serializer_class = WalletSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfExchangeAccount] # باید مالک حساب صرافی مربوطه باشد

    def get_queryset(self):
        # کاربر فقط می‌تواند کیف پول‌های مربوط به حساب‌های خود را ببیند
        return Wallet.objects.filter(exchange_account__user=self.request.user)


class WalletBalanceViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    queryset = WalletBalance.objects.all()
    serializer_class = WalletBalanceSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfExchangeAccount] # باید مالک حساب صرافی مربوطه باشد

    def get_queryset(self):
        # کاربر فقط می‌تواند موجودی‌های مربوط به حساب‌های خود را ببیند
        return WalletBalance.objects.filter(wallet__exchange_account__user=self.request.user)


class AggregatedPortfolioViewSet(SecureModelViewSet):
    serializer_class = AggregatedPortfolioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # فقط پرتفوی کاربر فعلی
        return AggregatedPortfolio.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # اطمینان از اینکه کاربر نمی‌تواند پرتفوی دیگری ایجاد کند
        user = self.request.user
        if AggregatedPortfolio.objects.filter(user=user).exists():
            raise ValidationError("Portfolio already exists for this user.")
        serializer.save(user=user)


class AggregatedAssetPositionViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    serializer_class = AggregatedAssetPositionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # فقط پوزیشن‌های مربوط به پرتفوی کاربر فعلی
        user_portfolio = AggregatedPortfolio.objects.filter(user=self.request.user).first()
        if user_portfolio:
            return AggregatedAssetPosition.objects.filter(aggregated_portfolio=user_portfolio)
        else:
            # اگر پرتفوی وجود نداشت، لیست خالی برگردان
            return AggregatedAssetPosition.objects.none()


class OrderHistoryViewSet(viewsets.ReadOnlyModelViewSet): # معمولاً فقط خواندنی
    serializer_class = OrderHistorySerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOfExchangeAccount] # باید مالک حساب صرافی مربوطه باشد

    def get_queryset(self):
        # کاربر فقط می‌تواند تاریخچه سفارشات مربوط به حساب‌های خود را ببیند
        return OrderHistory.objects.filter(exchange_account__user=self.request.user)


class MarketDataCandleViewSet(viewsets.ReadOnlyModelViewSet): # فقط خواندنی
    serializer_class = MarketDataCandleSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly] # یا فقط IsAuthenticated

    def get_queryset(self):
        # امکان فیلتر کردن بر اساس exchange، symbol، interval
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

        return queryset.order_by('open_time') # مرتب سازی بر اساس زمان باز

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticatedOrReadOnly])
    def latest(self, request):
        """
        Returns the latest candle for a given symbol and interval.
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
            # لاگ کنید
            return Response({"error": "An error occurred fetching the latest candle."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
