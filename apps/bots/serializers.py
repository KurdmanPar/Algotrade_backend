# apps/bots/serializers.py
from rest_framework import serializers
from .models import Bot, BotStrategyConfig
from apps.strategies.models import StrategyVersion
from apps.exchanges.models import ExchangeAccount
# from .connector_utils import BinanceConnector # <--- این خط را اضافه کنید
from apps.connectors.registry import get_connector

class BotStrategyConfigSerializer(serializers.ModelSerializer):
    """
    Serializer برای مدل BotStrategyConfig.
    """

    class Meta:
        model = BotStrategyConfig
        fields = ['id', 'strategy_version', 'weight', 'is_primary', 'parameters_override']


class BotSerializer(serializers.ModelSerializer):
    """
    Serializer اصلی برای مدل Bot.
    """
    ########################################## new
    # class Meta:
    #     model = Bot
    #     fields = [
    #         'id', 'name', 'description', 'bot_type', 'status', 'mode',
    #         'max_concurrent_trades', 'desired_profit_target_percent', 'max_allowed_loss_percent',
    #         'paper_trading_balance', 'schedule_config',
    #         'exchange_account', 'instrument', 'strategy_configs'
    #     ]
    #     read_only_fields = ['created_at', 'updated_at']
    ##########################################

    # برای نمایش اطلاعات مربوط به استراتژی‌های متصل به بات
    strategy_configs = BotStrategyConfigSerializer(source='strategy_configs', many=True, read_only=True)

    # برای نمایش اطلاعات صرافی حساب کاربر
    exchange_account_details = serializers.CharField(source='exchange_account.label', read_only=True)

    class Meta:
        model = Bot
        # فیلدهایی که در API نمایش یا دریافت می‌شوند
        fields = [
            'id', 'name', 'description', 'bot_type', 'status', 'mode', 'control_type',
            'max_concurrent_trades', 'desired_profit_target_percent', 'max_allowed_loss_percent',
            'paper_trading_balance', 'schedule_config', 'created_at', 'updated_at',
            'exchange_account', 'exchange_account_details', 'instrument', 'strategy_configs'
        ]
        read_only_fields = ['created_at', 'updated_at']  # این فیلدها را کاربر نمی‌تواند تغییر دهد

    def to_representation(self, instance):
        """
        برای سفارشی‌سازی خروجی API (مثلاً تبدیل ID به نام).
        """
        data = super().to_representation(instance)
        # اضافه کردن نام کامل استراتژی برای درک بهتر
        if instance.strategy_configs.exists():
            primary_strategy = instance.strategy_configs.get(is_primary=True)
            if primary_strategy:
                data['primary_strategy_name'] = primary_strategy.strategy_version.strategy.name
        return data