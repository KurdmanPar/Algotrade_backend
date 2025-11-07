# backend/trading/views.py




from rest_framework import viewsets, permissions, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import action  # این خط را اضافه کنید
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from .models import User, Role, Strategy, Indicator, Bot, Trade, Signal
from .serializers import (
    UserSerializer, RoleSerializer, StrategySerializer,
    IndicatorSerializer, BotSerializer, TradeSerializer, SignalSerializer
)
from .strategy_logic import MovingAverageCrossoverStrategy
import pandas as pd




class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت مدل کاربر.
    - اکشن 'create' (ثبت‌نام) برای همه باز است.
    - بقیه اکشن‌ها فقط برای خود کاربر قابل دسترسی هستند.
    """
    queryset = User.objects.all()  # این خط برای روتر ضروری است
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action == 'create':
            permission_classes = [AllowAny]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]

    def get_queryset(self):
        if self.request.user.is_staff:
            return User.objects.all()
        return User.objects.filter(id=self.request.user.id)


class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [IsAuthenticated]




class StrategyViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت استراتژی‌ها. هر کاربر فقط استراتژی‌های خودش را می‌بیند.
    """
    queryset = Strategy.objects.all()  # این خط برای روتر ضروری است
    serializer_class = StrategySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # این متد در زمان اجرا فراخوانی می‌شود و کوئری را فیلتر می‌کند
        return Strategy.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        """
        اطمینان حاصل می‌کند که استراتژی جدید به کاربر لاگین شده اختصاص داده می‌شود.
        """
        serializer.save(owner=self.request.user)



class IndicatorViewSet(viewsets.ModelViewSet):
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer
    permission_classes = [IsAuthenticated]




class TradeViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت معاملات. هر کاربر فقط معاملات مربوط به بات‌های خودش را می‌بیند.
    """
    queryset = Trade.objects.all()  # این خط برای روتر ضروری است
    serializer_class = TradeSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Trade.objects.filter(bot__user=self.request.user)


class SignalViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت سیگنال‌ها. هر کاربر فقط سیگنال‌های مربوط به استراتژی‌های خودش را می‌بیند.
    """
    queryset = Signal.objects.all()  # این خط برای روتر ضروری است
    serializer_class = SignalSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Signal.objects.filter(strategy__owner=self.request.user)


class CustomObtainAuthToken(ObtainAuthToken):
    """
    ویوی سفارشی برای ورود کاربر و دریافت توکن.
    این ویو علاوه بر توکن، اطلاعات کاربر را نیز برمی‌گرداند.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(data=request.data,
                                           context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_id': user.pk,
            'username': user.username,
            'email': user.email
        })

######################################




# ... سایر ویوها ...

class BotViewSet(viewsets.ModelViewSet):
    """
    ViewSet برای مدیریت بات‌ها. هر کاربر فقط بات‌های خودش را می‌بیند.
    """
    queryset = Bot.objects.all()  # این خط برای روتر ضروری است
    serializer_class = BotSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Bot.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        """
        اطمینان حاصل می‌کند که بات جدید به کاربر لاگین شده اختصاص داده می‌شود.
        """
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def run_backtest(self, request, pk=None):
        """
        یک بک‌تست ساده برای بات مورد نظر اجرا می‌کند.
        فعلاً از داده‌های قیمتی ساختگی استفاده می‌کند.
        """
        bot = self.get_object()

        # بررسی می‌کنیم که بات یک استراتژی دارد
        if not bot.strategy:
            return Response(
                {"error": "This bot is not assigned a strategy."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. ایجاد داده‌های قیمتی ساختگی
        # در یک سیستم واقعی، این داده‌ها از یک API خارجی دریافت می‌شوند
        price_data = pd.DataFrame(
            data={
                'close': [100, 101, 99, 102, 98, 103, 105, 104, 106, 107,
                          110, 112, 115, 118, 120, 125, 128, 130, 132, 135,
                          133, 130, 125, 120, 115, 110, 105, 100, 95, 90]
            },
            index=pd.date_range(start='2023-01-01', periods=30, freq='D')
        )

        # 2. اجرای استراتژی
        # در آینده، این بخش باید بر اساس نوع استراتژی (bot.strategy.type) تصمیم‌گیری کند
        strategy_logic = MovingAverageCrossoverStrategy()
        signals = strategy_logic.generate_signals(price_data)

        # 3. محاسبه نتایج ساده
        buy_signals = signals[signals['positions'] > 0]
        sell_signals = signals[signals['positions'] < 0]

        # 4. بازگرداندن نتایج
        results = {
            "bot_id": bot.id,
            "bot_name": bot.name,
            "strategy": bot.strategy.name,
            "symbol": bot.symbol,
            "initial_capital": 10000,  # فرضی
            "final_capital": 10500,  # فرضی
            "total_return": "5.00%",
            "buy_signals": buy_signals.index.strftime('%Y-%m-%d').tolist(),
            "sell_signals": sell_signals.index.strftime('%Y-%m-%d').tolist(),
            "signals_chart": signals.to_dict('records')  # برای نمایش در فرانت‌اند
        }

        return Response(results)