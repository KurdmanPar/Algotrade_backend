# # apps/bots/views.py
# from rest_framework import viewsets, status
# from rest_framework.decorators import action
# from rest_framework.response import Response
# from django.shortcuts import get_object_or_404
#
# # ایمپورت صحیح از ابزارهای اتصال
# from apps.connectors.registry import get_connector
# from apps.bots.models import Bot, BotStrategyConfig
# from apps.bots.serializers import BotSerializer, BotStrategyConfigSerializer
# from apps.strategies.models import StrategyVersion

# اگر نیاز به توابع اجرایی دارید، آن‌ها را اینجا تعریف کنید
# def execute_trade(bot_id: int, symbol: str, side: str, quantity: float):
#     ...

# apps/bots/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Bot, BotStrategyConfig
from .serializers import BotSerializer, BotStrategyConfigSerializer
from apps.strategies.models import StrategyVersion
from apps.connectors.connector_utils import get_bot_connector


# class BotViewSet(viewsets.ModelViewSet):
#     """
#     یک ViewSet برای ارائه عملیات CRUD برای مدل Bot.
#     ModelViewSet به طور خودکار عملیات list, create, retrieve, update, destroy را فراهم می‌کند.
#     """
#     serializer_class = BotSerializer
#
#     # فیلتر کردن بوت‌ها بر اساس کاربر لاگین کرده
#     def get_queryset(self):
#         return Bot.objects.filter(owner=self.request.user)
#
#     def perform_create(self, serializer):
#         """
#         هنگام ایجاد بات جدید، owner را به کاربر لاگین کرده تنظیم می‌کنیم.
#         """
#         serializer.save(owner=self.request.user)
#
#     @action(detail=True, methods=['post'])
#     def start(self, request, pk=None):
#         """
#         یک اکشن سفارشی برای شروع یک بات خاص.
#         مسیر API: POST /api/bots/{id}/start/
#         """
#         bot = self.get_object()
#         # در اینجا منطق شروع بات (مثلاً تغییر status و ارسال سیگنال به Agent) قرار می‌گیرد
#         bot.status = 'ACTIVE'
#         bot.save()
#         return Response({'status': 'bot started successfully'}, status=status.HTTP_200_OK)


class BotViewSet(viewsets.ModelViewSet):
    serializer_class = BotSerializer
    queryset = Bot.objects.all()

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    @action(detail=True, methods=['post'])
    def start(self, request, pk=None):
        bot = self.get_object()
        connector = get_bot_connector(bot)
        if connector and connector.connect():
            bot.status = 'ACTIVE'
            bot.save()
            return Response({'status': 'bot started successfully'}, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Failed to connect to exchange'}, status=status.HTTP_400_BAD_REQUEST)


    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """
        یک اکشن سفارشی برای توقف یک بات خاص.
        مسیر API: POST /api/bots/{id}/stop/
        """
        bot = self.get_object()
        bot.status = 'STOPPED'
        bot.save()
        return Response({'status': 'bot stopped successfully'}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def add_strategy(self, request, pk=None):
        """
        اکشنی برای اضافه کردن یک استراتژی به یک بات.
        انتظار می‌رود payload شامل {'strategy_version_id': 1, 'weight': 1.0}
        """
        bot = self.get_object()
        strategy_version_id = request.data.get('strategy_version_id')
        weight = request.data.get('weight', 1.0)

        if not strategy_version_id:
            return Response({'error': 'strategy_version_id is required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            strategy_version = StrategyVersion.objects.get(id=strategy_version_id)
        except StrategyVersion.DoesNotExist:
            return Response({'error': 'Invalid strategy_version_id'}, status=status.HTTP_404_NOT_FOUND)

        # بررسی اینکه آیا این ترکیب بات و استراتژی از قبل وجود دارد
        if BotStrategyConfig.objects.filter(bot=bot, strategy_version=strategy_version).exists():
            return Response({'error': 'This strategy is already added to this bot.'},
                            status=status.HTTP_400_BAD_REQUEST)

        BotStrategyConfig.objects.create(
            bot=bot,
            strategy_version=strategy_version,
            weight=weight
        )

        serializer = BotSerializer(bot)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
