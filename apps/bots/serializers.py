# apps/bots/serializers.py
from rest_framework import serializers
from .models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot
from apps.accounts.serializers import UserSerializer  # اگر نیاز باشد
from apps.exchanges.serializers import ExchangeAccountSerializer
from apps.instruments.serializers import InstrumentSerializer
from apps.strategies.serializers import StrategyVersionSerializer
from apps.risk.serializers import RiskProfileSerializer  # فقط اگر در مدل Bot فیلد risk_profile باشد

class BotSerializer(serializers.ModelSerializer):
    # اگر مدل Bot دارای فیلد risk_profile باشد، آن را اینجا اضافه کنید
    # risk_profile = RiskProfileSerializer(read_only=True)

    class Meta:
        model = Bot
        fields = '__all__'
        read_only_fields = ('owner',)  # owner باید خودکار ست شود

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['owner'] = user
        return super().create(validated_data)


class BotStrategyConfigSerializer(serializers.ModelSerializer):
    strategy_version = StrategyVersionSerializer(read_only=True)

    class Meta:
        model = BotStrategyConfig
        fields = '__all__'


class BotLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotLog
        fields = '__all__'


class BotPerformanceSnapshotSerializer(serializers.ModelSerializer):
    class Meta:
        model = BotPerformanceSnapshot
        fields = '__all__'