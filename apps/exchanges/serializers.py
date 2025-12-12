# apps/exchanges/serializers.py

from rest_framework import serializers
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
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
from apps.core.models import BaseOwnedModel # import برای بررسی ارث‌بری
from apps.core.helpers import validate_ip_list, mask_sensitive_data # import از core
from apps.core.exceptions import CoreSystemException, SecurityException # import از core
from apps.bots.models import TradingBot # import از اپلیکیشن دیگر
from apps.accounts.models import CustomUser # import از اپلیکیشن دیگر
from apps.instruments.models import Instrument # import از اپلیکیشن دیگر
from apps.exchanges.models import InstrumentExchangeMap # import از این اپلیکیشن (اگر وجود داشته باشد)
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class ExchangeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exchange
        fields = '__all__'
        # اطمینان از اینکه فیلدهای پایه از BaseModel (id, created_at, updated_at) نیز گرفته شوند


class ExchangeAccountSerializer(serializers.ModelSerializer):
    """
    Serializer for ExchangeAccount model.
    Handles encryption of API keys on creation/update and masking on retrieval.
    """
    # ارتباط با بات‌ها به صورت IDها
    linked_bots = serializers.PrimaryKeyRelatedField(
        queryset=TradingBot.objects.all(),
        many=True,
        required=False,
        help_text=_("List of bot IDs to link to this account.")
    )
    # فیلدهای API Key/Secret به صورت write-only (فقط برای ارسال)
    api_key = serializers.CharField(write_only=True, help_text=_("Plain text API key. Will be encrypted."))
    api_secret = serializers.CharField(write_only=True, help_text=_("Plain text API secret. Will be encrypted."))

    class Meta:
        model = ExchangeAccount
        fields = [
            'id', 'owner', 'exchange', 'label', 'api_key', 'api_secret', 'extra_credentials',
            'is_active', 'is_paper_trading', 'last_sync_at', 'last_login_ip', 'created_ip',
            'account_info', 'trading_permissions', 'linked_bots',
            # فیلدهای read_only از BaseModel و BaseOwnedModel
            'created_at', 'updated_at'
        ]
        read_only_fields = ('owner', 'created_at', 'updated_at', 'last_sync_at')

    def create(self, validated_data):
        """
        Creates an ExchangeAccount, encrypts API keys, and links bots.
        """
        user = self.context['request'].user # اطمینان از احراز هویت کاربر در نما
        linked_bots = validated_data.pop('linked_bots', [])

        # اطمینان از اینکه owner از context تنظیم می‌شود، نه از validated_data
        validated_data['owner'] = user

        # گرفتن و رمزنگاری کلیدها
        api_key = validated_data.pop('api_key')
        api_secret = validated_data.pop('api_secret')

        instance = super().create(validated_data)

        # اعمال کلیدها (که در مدل از طریق propertyها رمزنگاری می‌شوند)
        instance.api_key = api_key
        instance.api_secret = api_secret
        instance.save(update_fields=['_api_key_encrypted', '_api_secret_encrypted', 'encrypted_key_iv']) # فقط فیلدهای رمزنگاری شده را ذخیره کن

        # لینک کردن بات‌ها
        if linked_bots:
            instance.linked_bots.set(linked_bots)

        logger.info(f"ExchangeAccount for {instance.exchange.name} created for user {user.email}.")
        return instance

    def update(self, instance, validated_data):
        """
        Updates an ExchangeAccount, handles API key encryption if provided.
        """
        linked_bots = validated_data.pop('linked_bots', None)

        # مدیریت به‌روزرسانی کلیدها (اختیاری)
        api_key = validated_data.pop('api_key', None)
        api_secret = validated_data.pop('api_secret', None)
        if api_key:
            instance.api_key = api_key
        if api_secret:
            instance.api_secret = api_secret

        # owner نباید تغییر کند
        validated_data.pop('owner', None)

        instance = super().update(instance, validated_data)

        # ذخیره کلیدها اگر تغییر کرده بودند
        update_fields = ['updated_at']
        if api_key or api_secret:
            update_fields.extend(['_api_key_encrypted', '_api_secret_encrypted', 'encrypted_key_iv'])
        instance.save(update_fields=update_fields)

        # بات‌ها را بروزرسانی کن
        if linked_bots is not None:
            instance.linked_bots.set(linked_bots)

        logger.info(f"ExchangeAccount {instance.label} for {instance.exchange.name} updated by user {instance.owner.email}.")
        return instance

    def to_representation(self, instance):
        """
        Override to_representation to mask sensitive API key/secret values on read.
        """
        data = super().to_representation(instance)
        # اگر فیلد api_key در خروجی وجود داشت (که نباید بود، چون write_only است)، مسک کن
        # اما اگر مدل فیلدی داشت که همیشه نمایش داده می‌شود، باید در مدل یا اینجا مسک شود
        # از آنجا که api_key و api_secret write_only هستند، در خروجی JSON ظاهر نمی‌شوند
        # اما اگر فیلد دیگری وجود داشت که نیاز به مسک کردن داشت، اینجا انجام می‌شود
        # مثلاً اگر فیلدی به نام 'details' وجود داشت که شامل اطلاعات حساس بود
        # if 'details' in data and any(keyword in instance.key for keyword in ['api', 'key', 'secret']):
        #     data['details'] = mask_sensitive_data(data['details'])
        return data


class WalletSerializer(serializers.ModelSerializer):
    """
    Serializer for Wallet model.
    """
    # نمایش اطلاعات مربوط به حساب صرافی
    exchange_account_label = serializers.CharField(source='exchange_account.label', read_only=True)
    exchange_name = serializers.CharField(source='exchange_account.exchange.name', read_only=True)

    class Meta:
        model = Wallet
        fields = [
            'id', 'exchange_account', 'exchange_account_label', 'exchange_name', 'wallet_type', 'description',
            'is_default', 'is_margin_enabled', 'leverage', 'borrowed_amount',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at', 'owner') # owner از exchange_account است

    def validate_leverage(self, value):
        """
        Validates the leverage value against the exchange's max_leverage.
        This requires accessing the related ExchangeAccount's details, which might need a custom method or view logic.
        For now, a simple check against a global max.
        """
        if value and value > Decimal('125'): # فرض: حداکثر لوریج جهانی
            raise ValidationError(_("Leverage cannot exceed 125x."))
        return value


class WalletBalanceSerializer(serializers.ModelSerializer):
    """
    Serializer for WalletBalance model.
    """
    wallet_type = serializers.CharField(source='wallet.wallet_type', read_only=True)
    exchange_account_label = serializers.CharField(source='wallet.exchange_account.label', read_only=True)
    exchange_name = serializers.CharField(source='wallet.exchange_account.exchange.name', read_only=True)

    class Meta:
        model = WalletBalance
        fields = [
            'id', 'wallet', 'wallet_type', 'exchange_account_label', 'exchange_name', 'asset_symbol',
            'total_balance', 'available_balance', 'in_order_balance', 'frozen_balance', 'borrowed_balance',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        """
        Validates balance fields against each other.
        e.g., available_balance + frozen_balance + borrowed_balance <= total_balance
        """
        total = attrs.get('total_balance', Decimal('0'))
        available = attrs.get('available_balance', Decimal('0'))
        frozen = attrs.get('frozen_balance', Decimal('0'))
        borrowed = attrs.get('borrowed_balance', Decimal('0'))
        in_orders = attrs.get('in_order_balance', Decimal('0'))

        # محاسبه موجودی قابل معامله
        calc_available = total - frozen - borrowed - in_orders
        if available != calc_available:
             raise ValidationError(_("Available balance does not match calculated value (Total - Frozen - Borrowed - In Orders)."))

        # اطمینان از اینکه مبالغ منفی نیستند
        for field_name in ['total_balance', 'available_balance', 'frozen_balance', 'borrowed_balance', 'in_order_balance']:
            val = attrs.get(field_name)
            if val is not None and val < 0:
                raise ValidationError({field_name: _("Balance cannot be negative.")})

        return attrs


class AggregatedPortfolioSerializer(serializers.ModelSerializer):
    """
    Serializer for AggregatedPortfolio model.
    """
    owner_email = serializers.CharField(source='owner.email', read_only=True) # نمایش ایمیل مالک

    class Meta:
        model = AggregatedPortfolio
        fields = [
            'id', 'owner', 'owner_email', 'base_currency', 'total_equity', 'total_unrealized_pnl',
            'total_realized_pnl', 'total_pnl_percentage', 'total_commission_paid', 'total_funding_fees',
            'last_valuation_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ('owner', 'created_at', 'updated_at') # owner از context تعیین می‌شود

    def create(self, validated_data):
        """
        Override create to set the owner from the request context.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        else:
            raise ValidationError("Request context is required to determine the owner.")
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Override update to prevent changing the owner.
        """
        validated_data.pop('owner', None) # جلوگیری از تغییر owner
        return super().update(instance, validated_data)


class AggregatedAssetPositionSerializer(serializers.ModelSerializer):
    """
    Serializer for AggregatedAssetPosition model.
    """
    portfolio_owner_email = serializers.CharField(source='aggregated_portfolio.owner.email', read_only=True)

    class Meta:
        model = AggregatedAssetPosition
        fields = [
            'id', 'aggregated_portfolio', 'portfolio_owner_email', 'asset_symbol',
            'total_quantity', 'total_value_in_base_currency', 'per_exchange_breakdown',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def validate_per_exchange_breakdown(self, value):
        """
        Validates the structure of the per_exchange_breakdown JSON field.
        Example: Checks if it's a dictionary and has expected keys per exchange.
        """
        if not isinstance(value, dict):
            raise ValidationError(_("Per exchange breakdown must be a JSON object."))

        # منطق اعتبارسنجی سفارشی برای ساختار JSON
        # مثلاً بررسی اینکه هر کلید یک کد صرافی معتبر باشد و مقادیر شامل 'quantity', 'value' باشند
        # valid_exchange_codes = [ex.code for ex in Exchange.objects.all()] # یا از کش استفاده کنید
        # for exchange_code, details in value.items():
        #     if exchange_code.upper() not in valid_exchange_codes:
        #         raise ValidationError(f"Invalid exchange code '{exchange_code}' in breakdown.")
        #     if not isinstance(details, dict) or 'quantity' not in details or 'value' not in details:
        #         raise ValidationError(f"Invalid structure for exchange '{exchange_code}' in breakdown.")
        #     # ... اعتبارسنجی‌های بیشتر ...
        return value


class OrderHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for OrderHistory model.
    """
    exchange_account_label = serializers.CharField(source='exchange_account.label', read_only=True)
    exchange_name = serializers.CharField(source='exchange_account.exchange.name', read_only=True)
    bot_name = serializers.CharField(source='trading_bot.name', read_only=True, allow_null=True)

    class Meta:
        model = OrderHistory
        fields = [
            'id', 'exchange_account', 'exchange_account_label', 'exchange_name', 'order_id', 'symbol',
            'side', 'order_type', 'status', 'price', 'quantity', 'executed_quantity', 'cumulative_quote_qty',
            'time_placed', 'time_updated', 'commission', 'commission_asset', 'trading_bot', 'bot_name',
            'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

    # ممکن است نیاز به اعتبارسنجی داده‌های ورودی داشته باشید (مثلاً اطمینان از اینکه order_id منحصر به فرد است برای این حساب)
    # def validate(self, attrs):
    #     exchange_account = attrs.get('exchange_account')
    #     order_id = attrs.get('order_id')
    #     if exchange_account and order_id:
    #         if OrderHistory.objects.filter(exchange_account=exchange_account, order_id=order_id).exists():
    #             raise ValidationError("An order with this ID already exists for this exchange account.")
    #     return attrs


class MarketDataCandleSerializer(serializers.ModelSerializer):
    """
    Serializer for MarketDataCandle model.
    """
    exchange_name = serializers.CharField(source='exchange.name', read_only=True)

    class Meta:
        model = MarketDataCandle
        fields = [
            'id', 'exchange', 'exchange_name', 'symbol', 'interval', 'open_time', 'open', 'high', 'low', 'close',
            'volume', 'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        """
        Validates OHLCV data consistency.
        e.g., Low <= Open <= High, Low <= Close <= High, Volume >= 0
        """
        open_price = attrs.get('open', Decimal('0'))
        high_price = attrs.get('high', Decimal('0'))
        low_price = attrs.get('low', Decimal('0'))
        close_price = attrs.get('close', Decimal('0'))
        volume = attrs.get('volume', Decimal('0'))

        if volume < 0:
            raise ValidationError({"volume": _("Volume cannot be negative.")})

        # اعتبارسنجی منطق قیمت
        if not (low_price <= open_price <= high_price and low_price <= close_price <= high_price):
             hp = float(high_price)
             lp = float(low_price)
             op = float(open_price)
             cp = float(close_price)
             raise ValidationError(f"OHLCV prices are inconsistent: L:{lp} O:{op} H:{hp} C:{cp}")

        if high_price < low_price:
            raise ValidationError({"high": _("High price cannot be less than Low price.")})

        return attrs

# --- سریالایزرهایی که از Core ارث می‌برند ---
# این سریالایزرها می‌توانند در اپلیکیشن‌های دیگر نیز استفاده شوند
# مثال: اگر یک مدل جدید در instruments یا یک مدل دیگر در exchanges وجود داشت که از BaseOwnedModel ارث می‌برد
# class SomeOwnedModelSerializer(CoreOwnedModelSerializer): # فرض: CoreOwnedModelSerializer در apps.core.serializers وجود دارد
#     class Meta(CoreOwnedModelSerializer.Meta):
#         model = SomeOwnedModel
#         fields = CoreOwnedModelSerializer.Meta.fields + ['specific_field_1', 'specific_field_2']

logger.info("Exchanges serializers loaded successfully.")
