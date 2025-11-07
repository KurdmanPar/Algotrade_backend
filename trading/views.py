from rest_framework import viewsets
from .models import User, Role, Strategy, Indicator, Bot, Trade, Signal
from .serializers import UserSerializer, RoleSerializer, StrategySerializer, IndicatorSerializer, BotSerializer, TradeSerializer, SignalSerializer

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer

class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer

class StrategyViewSet(viewsets.ModelViewSet):
    queryset = Strategy.objects.all()
    serializer_class = StrategySerializer

class IndicatorViewSet(viewsets.ModelViewSet):
    queryset = Indicator.objects.all()
    serializer_class = IndicatorSerializer

class BotViewSet(viewsets.ModelViewSet):
    queryset = Bot.objects.all()
    serializer_class = BotSerializer

class TradeViewSet(viewsets.ModelViewSet):
    queryset = Trade.objects.all()
    serializer_class = TradeSerializer

class SignalViewSet(viewsets.ModelViewSet):
    queryset = Signal.objects.all()
    serializer_class = SignalSerializer


# Create your views here.
