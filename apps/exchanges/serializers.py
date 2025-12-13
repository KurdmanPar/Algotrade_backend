# apps/exchanges/serializers.py

from rest_framework import serializers
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
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
from apps.core.serializers import CoreBaseSerializer, CoreOwnedModelSerializer # استفاده از سریالایزرهای پایه core
from apps.core.helpers import validate_ip_list # استفاده از تابع کمکی core
from apps.core.exceptions import DataIntegrityException # استفاده از استثناهای core
from apps.accounts.models import CustomUser # اطمینان از وجود مدل کاربر
from apps.bots.models import TradingBot # اطمینان از وجود مدل بات
from apps.exchanges.models import InstrumentExchangeMap # import از این اپلیکیشن (اگر نیاز باشد)
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class ExchangeSerializer(CoreBaseSerializer): # ارث از CoreBaseSerializer
    """
    Serializer for the Exchange model.
    Uses CoreBaseSerializer for common fields like id, created_at, updated_at.
    """
    class Meta(CoreBaseSerializer.Meta): # ارث از Meta CoreBaseSerializer
        model = Exchange
        fields = CoreBaseSerializer.Meta.fields + [ # افزودن فیلدهای خاص Exchange
            'name', 'code', 'type', 'base_url', 'ws_url', 'api_docs_url',
            'is_active', 'is_sandbox', 'rate_limit_per_second',
            'fees_structure', 'limits'
        ]

    def validate_code(self, value):
        """
        Validates the uniqueness of the exchange code (case-insensitive).
        Note: The constraint is also defined in the model.
        """
        if Exchange.objects.filter(code__iexact=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError(_("An exchange with this code already exists."))
        return value

    def validate_base_url(self, value):
        """
        Validates the base_url format using Django's built-in validator.
        """
        validator = URLValidator()
        try:
            validator(value)
            return value
        except DjangoValidationError:
            raise serializers.ValidationError(_("Enter a valid URL for the base API URL."))

    def validate_ws_url(self, value):
        """
        Validates the WebSocket URL format.
        """
        if value: # فقط اگر مقداری وجود داشت
            validator = URLValidator()
            try:
                validator(value)
                return value
            except DjangoValidationError:
                raise serializers.ValidationError(_("Enter a valid URL for the WebSocket URL."))


class ExchangeAccountSerializer(CoreOwnedModelSerializer): # ارث از CoreOwnedModelSerializer
    """
    Serializer for the ExchangeAccount model.
    Uses CoreOwnedModelSerializer for owner, created_at, updated_at.
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

    # افزودن فیلد برای نمایش نام صرافی
    exchange_name = serializers.CharField(source='exchange.name', read_only=True)

    class Meta(CoreOwnedModelSerializer.Meta): # ارث از Meta CoreOwnedModelSerializer
        model = ExchangeAccount
        fields = CoreOwnedModelSerializer.Meta.fields + [ # افزودن فیلدهای خاص ExchangeAccount
            'exchange', 'exchange_name', 'label',
            'api_key', 'api_secret', 'extra_credentials',
            'is_active', 'is_paper_trading', 'last_sync_at',
            'last_login_ip', 'created_ip',
            'account_info', 'trading_permissions',
            'linked_bots',
        ]
        read_only_fields = CoreOwnedModelSerializer.Meta.read_only_fields + ('last_sync_at',)

    def create(self, validated_data):
        """
        Creates an ExchangeAccount, encrypts API keys, and links bots.
        """
        # user = self.context['request'].user # این باید در نما انجام شود و در validated_data نباشد
        linked_bots = validated_data.pop('linked_bots', [])

        # گرفتن و رمزنگاری کلیدها
        api_key = validated_data.pop('api_key')
        api_secret = validated_data.pop('api_secret')

        # ایجاد نمونه
        instance = super().create(validated_data)

        # اعمال کلیدها (که در مدل از طریق propertyها رمزنگاری می‌شوند)
        instance.api_key = api_key
        instance.api_secret = api_secret
        # ذخیره فقط فیلدهای رمزنگاری شده
        instance.save(update_fields=['_api_key_encrypted', '_api_secret_encrypted', 'encrypted_key_iv'])

        # لینک کردن بات‌ها
        if linked_bots:
            instance.linked_bots.set(linked_bots)

        logger.info(f"ExchangeAccount for {instance.exchange.name} created for user {instance.owner.email}.") # تغییر: owner به جای user
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

        # owner نباید تغییر کند (که در CoreOwnedModelSerializer از قبل چک می‌شود)
        # validated_data.pop('owner', None) # این نیز در CoreOwnedModelSerializer انجام می‌شود

        instance = super().update(instance, validated_data)

        # ذخیره کلیدها اگر تغییر کرده بودند
        update_fields = ['updated_at']
        if api_key or api_secret:
            instance.save(update_fields=['_api_key_encrypted', '_api_secret_encrypted', 'encrypted_key_iv', 'updated_at'])
        else:
            instance.save(update_fields=update_fields)

        # بات‌ها را بروزرسانی کن
        if linked_bots is not None:
            instance.linked_bots.set(linked_bots)

        logger.info(f"ExchangeAccount {instance.label} for {instance.exchange.name} updated by user {instance.owner.email}.")
        return instance

    def to_representation(self, instance):
        """
        Override to_representation to mask sensitive API key/secret values on read.
        This is done by not including the write-only fields in the output.
        The api_key and api_secret fields are write-only, so they won't appear in the JSON output.
        """
        data = super().to_representation(instance)
        # چون api_key و api_secret write_only هستند، در خروجی نمایش داده نمی‌شوند.
        # اما اگر فیلدی وجود داشت که نیاز به مسک کردن داشت (مثلاً یک فیلد 'details' حاوی داده حساس)
        # if 'details' in data:
        #     data['details'] = mask_sensitive_data(data['details'])
        return data

    def validate(self, attrs):
        """
        Validates the ExchangeAccount data.
        e.g., checks if the exchange is active, validates extra_credentials format.
        """
        exchange = attrs.get('exchange')
        if exchange and not exchange.is_active:
             raise serializers.ValidationError({'exchange': _("Selected exchange is not active.")})

        extra_creds = attrs.get('extra_credentials')
        if extra_creds:
            if not isinstance(extra_creds, dict):
                raise serializers.ValidationError({'extra_credentials': _("Must be a valid JSON object.")})
            # می‌توانید اعتبارسنجی‌های بیشتری برای ساختار داخل extra_credentials اضافه کنید
            # مثلاً بررسی وجود فیلدهای خاص یا نوع داده‌ها
            # required_creds = ['api_key', 'api_secret'] # مثال
            # for cred in required_creds:
            #     if cred not in extra_creds:
            #         raise serializers.ValidationError({'extra_credentials': _(f"Missing required credential: {cred}")})

        # اعتبارسنجی IPهای ورودی (اگر نیاز باشد)
        created_ip = attrs.get('created_ip')
        last_login_ip = attrs.get('last_login_ip')
        if created_ip:
            if not validate_ip_list(created_ip): # استفاده از تابع کمکی core
                raise serializers.ValidationError({'created_ip': _("Invalid IP address format.")})
        if last_login_ip:
            if not validate_ip_list(last_login_ip): # استفاده از تابع کمکی core
                raise serializers.ValidationError({'last_login_ip': _("Invalid IP address format.")})

        return attrs


class WalletSerializer(CoreBaseSerializer):
    """
    Serializer for the Wallet model.
    """
    # افزودن فیلدهای مربوط به حساب صرافی
    exchange_account_label = serializers.CharField(source='exchange_account.label', read_only=True)
    exchange_name = serializers.CharField(source='exchange_account.exchange.name', read_only=True)

    class Meta(CoreBaseSerializer.Meta):
        model = Wallet
        fields = CoreBaseSerializer.Meta.fields + [
            'exchange_account', 'exchange_account_label', 'exchange_name', 'wallet_type', 'description',
            'is_default', 'is_margin_enabled', 'leverage', 'borrowed_amount'
        ]

    def validate_leverage(self, value):
        """
        Validates the leverage value against the exchange's max_leverage (if available).
        This requires accessing the related ExchangeAccount's details, which might need a custom method or view logic.
        For now, a simple check against a global max.
        """
        # این منطق نیازمند دسترسی به exchange_account دارد که در این مرحله ممکن است در validated_data نباشد
        # یا فقط در زمان بروزرسانی (instance) قابل دسترسی باشد
        # مثال ساده:
        if value and value > Decimal('125'): # فرض: حداکثر لوریج جهانی
            raise serializers.ValidationError(_("Leverage cannot exceed 125x."))
        return value

    def validate(self, attrs):
        """
        Validates wallet-specific data.
        e.g., checks if margin is enabled only for margin-type wallets.
        """
        wallet_type = attrs.get('wallet_type')
        is_margin_enabled = attrs.get('is_margin_enabled')
        leverage = attrs.get('leverage')

        if wallet_type not in ['MARGIN', 'ISOLATED_MARGIN'] and is_margin_enabled:
            raise serializers.ValidationError({'is_margin_enabled': _("Margin can only be enabled for Margin or Isolated Margin wallet types.")})

        if is_margin_enabled and (leverage is None or leverage < 1):
            raise serializers.ValidationError({'leverage': _("Leverage must be at least 1 when margin is enabled.")})

        return attrs


class WalletBalanceSerializer(CoreBaseSerializer):
    """
    Serializer for the WalletBalance model.
    """
    # افزودن فیلدهای مربوط به کیف پول
    wallet_type = serializers.CharField(source='wallet.wallet_type', read_only=True)
    exchange_account_label = serializers.CharField(source='wallet.exchange_account.label', read_only=True)
    exchange_name = serializers.CharField(source='wallet.exchange_account.exchange.name', read_only=True)

    class Meta(CoreBaseSerializer.Meta):
        model = WalletBalance
        fields = CoreBaseSerializer.Meta.fields + [
            'wallet', 'wallet_type', 'exchange_account_label', 'exchange_name', 'asset_symbol',
            'total_balance', 'available_balance', 'in_order_balance', 'frozen_balance', 'borrowed_balance'
        ]

    def validate(self, attrs):
        """
        Validates balance fields against each other.
        e.g., available_balance + frozen_balance + borrowed_balance + in_order_balance <= total_balance
        """
        total = attrs.get('total_balance', Decimal('0'))
        available = attrs.get('available_balance', Decimal('0'))
        frozen = attrs.get('frozen_balance', Decimal('0'))
        borrowed = attrs.get('borrowed_balance', Decimal('0'))
        in_orders = attrs.get('in_order_balance', Decimal('0'))

        # محاسبه موجودی قابل معامله
        calc_available = total - frozen - borrowed - in_orders
        if available != calc_available:
             raise serializers.ValidationError(_("Available balance does not match calculated value (Total - Frozen - Borrowed - In Orders)."))

        # اطمینان از اینکه مبالغ منفی نیستند
        for field_name in ['total_balance', 'available_balance', 'frozen_balance', 'borrowed_balance', 'in_order_balance']:
            val = attrs.get(field_name)
            if val is not None and val < 0:
                raise serializers.ValidationError({field_name: _("Balance cannot be negative.")})

        return attrs


class AggregatedPortfolioSerializer(CoreOwnedModelSerializer): # ارث از CoreOwnedModelSerializer
    """
    Serializer for the AggregatedPortfolio model.
    Uses CoreOwnedModelSerializer for owner, created_at, updated_at.
    """
    class Meta(CoreOwnedModelSerializer.Meta):
        model = AggregatedPortfolio
        fields = CoreOwnedModelSerializer.Meta.fields + [ # افزودن فیلدهای خاص پرتفوی
            'base_currency', 'total_equity', 'total_unrealized_pnl',
            'total_realized_pnl', 'total_pnl_percentage', 'total_commission_paid', 'total_funding_fees',
            'last_valuation_at'
        ]
        # owner از CoreOwnedModelSerializer ارث می‌برد و فقط خواندنی است یا از context تعیین می‌شود
        read_only_fields = CoreOwnedModelSerializer.Meta.read_only_fields

    def validate_base_currency(self, value):
        """
        Validates the base currency format (e.g., 3-letter code).
        """
        if not re.match(r'^[A-Z]{3,16}$', value): # مثال ساده
            raise serializers.ValidationError(_("Base currency must be a valid 3-16 letter code (e.g., USD, EUR, IRT)."))
        return value


class AggregatedAssetPositionSerializer(CoreBaseSerializer):
    """
    Serializer for the AggregatedAssetPosition model.
    """
    # افزودن فیلد برای نمایش ایمیل مالک پرتفوی
    portfolio_owner_email = serializers.CharField(source='aggregated_portfolio.owner.email', read_only=True)

    class Meta(CoreBaseSerializer.Meta):
        model = AggregatedAssetPosition
        fields = CoreBaseSerializer.Meta.fields + [
            'aggregated_portfolio', 'portfolio_owner_email', 'asset_symbol',
            'total_quantity', 'total_value_in_base_currency', 'per_exchange_breakdown'
        ]

    def validate_per_exchange_breakdown(self, value):
        """
        Validates the structure of the per_exchange_breakdown JSON field.
        Example: Checks if it's a dictionary and has expected keys per exchange.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError(_("Per exchange breakdown must be a JSON object."))

        # منطق اعتبارسنجی سفارشی برای ساختار JSON
        # مثلاً بررسی اینکه هر کلید یک کد صرافی معتبر باشد و مقادیر شامل 'quantity', 'value' باشند
        # valid_exchange_codes = [ex.code for ex in Exchange.objects.all()] # یا از کش استفاده کنید
        # for exchange_code, details in value.items():
        #     if exchange_code.upper() not in valid_exchange_codes:
        #         raise serializers.ValidationError(f"Invalid exchange code '{exchange_code}' in breakdown.")
        #     if not isinstance(details, dict) or 'quantity' not in details or 'value' not in details:
        #         raise serializers.ValidationError(f"Invalid structure for exchange '{exchange_code}' in breakdown.")
        #     # ... اعتبارسنجی‌های بیشتر ...
        return value

    def validate(self, attrs):
        """
        Validates consistency between total_quantity, total_value, and per_exchange_breakdown.
        """
        total_quantity = attrs.get('total_quantity', Decimal('0'))
        total_value = attrs.get('total_value_in_base_currency', Decimal('0'))
        breakdown = attrs.get('per_exchange_breakdown', {})

        # مثال: چک کردن اینکه مجموع مقادیر در breakdown با total_quantity برابر است
        # این فقط یک مثال است و ممکن است نیاز به تغییر داشته باشد
        sum_quantity_from_breakdown = sum(
            Decimal(str(item.get('quantity', 0))) for item in breakdown.values()
        )
        if total_quantity != sum_quantity_from_breakdown:
             raise serializers.ValidationError({"per_exchange_breakdown": _("Sum of quantities in breakdown does not match total_quantity.")})

        # مثال: چک کردن اینکه مجموع ارزش‌ها در breakdown با total_value برابر است
        sum_value_from_breakdown = sum(
            Decimal(str(item.get('value', 0))) for item in breakdown.values()
        )
        if total_value != sum_value_from_breakdown:
             raise serializers.ValidationError({"per_exchange_breakdown": _("Sum of values in breakdown does not match total_value_in_base_currency.")})

        return attrs


class OrderHistorySerializer(CoreBaseSerializer):
    """
    Serializer for the OrderHistory model.
    """
    # افزودن فیلدهای مربوط به حساب صرافی و بات
    exchange_account_label = serializers.CharField(source='exchange_account.label', read_only=True)
    exchange_name = serializers.CharField(source='exchange_account.exchange.name', read_only=True)
    bot_name = serializers.CharField(source='trading_bot.name', read_only=True, allow_null=True)

    class Meta(CoreBaseSerializer.Meta):
        model = OrderHistory
        fields = CoreBaseSerializer.Meta.fields + [
            'exchange_account', 'exchange_account_label', 'exchange_name', 'order_id', 'symbol',
            'side', 'order_type', 'status', 'price', 'quantity', 'executed_quantity', 'cumulative_quote_qty',
            'time_placed', 'time_updated', 'commission', 'commission_asset', 'trading_bot', 'bot_name',
        ]

    def validate(self, attrs):
        """
        Validates order history data.
        e.g., checks if status is consistent with filled amounts, side/type validity.
        """
        status = attrs.get('status')
        executed_qty = attrs.get('executed_quantity', Decimal('0'))
        quantity = attrs.get('quantity', Decimal('0'))
        side = attrs.get('side')
        order_type = attrs.get('order_type')

        # چک کردن وضعیت با مقدار اجرا شده
        if status == 'FILLED' and executed_qty != quantity:
            raise serializers.ValidationError({"status": _("Status 'FILLED' requires executed quantity to match total quantity.")})
        if status == 'CANCELED' and executed_qty == quantity:
            raise serializers.ValidationError({"status": _("Status 'CANCELED' is inconsistent with fully executed quantity. Use 'FILLED' instead.")})

        # چک کردن اینکه side و order_type معتبر باشند
        valid_sides = [choice[0] for choice in OrderHistory.SIDE_CHOICES]
        valid_types = [choice[0] for choice in OrderHistory.ORDER_TYPE_CHOICES]
        if side and side not in valid_sides:
            raise serializers.ValidationError({"side": _("Invalid order side.")})
        if order_type and order_type not in valid_types:
            raise serializers.ValidationError({"order_type": _("Invalid order type.")})

        # اطمینان از اینکه قیمت و مقدار مثبت هستند
        for field_name in ['price', 'quantity', 'executed_quantity', 'cumulative_quote_qty', 'commission']:
            val = attrs.get(field_name)
            if val is not None and val < 0:
                raise serializers.ValidationError({field_name: _("Value cannot be negative.")})

        # چک کردن اینکه آیا تاریخ ایجاد بعد از تاریخ بروزرسانی است
        time_placed = attrs.get('time_placed')
        time_updated = attrs.get('time_updated')
        if time_placed and time_updated and time_placed > time_updated:
             raise serializers.ValidationError({"time_updated": _("Update time cannot be earlier than placement time.")})

        return attrs


class MarketDataCandleSerializer(CoreBaseSerializer):
    """
    Serializer for the MarketDataCandle model.
    """
    # افزودن فیلد برای نمایش نام صرافی
    exchange_name = serializers.CharField(source='exchange.name', read_only=True)

    class Meta(CoreBaseSerializer.Meta):
        model = MarketDataCandle
        fields = CoreBaseSerializer.Meta.fields + [
            'exchange', 'exchange_name', 'symbol', 'interval', 'open_time', 'open', 'high', 'low', 'close',
            'volume', 'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume'
        ]

    def validate(self, attrs):
        """
        Validates OHLCV data consistency.
        e.g., Low <= Open <= High, Low <= Close <= High, Volume >= 0, Timestamp logic.
        """
        open_price = attrs.get('open', Decimal('0'))
        high_price = attrs.get('high', Decimal('0'))
        low_price = attrs.get('low', Decimal('0'))
        close_price = attrs.get('close', Decimal('0'))
        volume = attrs.get('volume', Decimal('0'))

        # چک کردن اعداد منفی
        if volume < 0:
            raise serializers.ValidationError({"volume": _("Volume cannot be negative.")})

        if open_price < 0 or high_price < 0 or low_price < 0 or close_price < 0:
            raise serializers.ValidationError(_("Prices must be non-negative."))

        # چک کردن منطق قیمت
        hp = float(high_price)
        lp = float(low_price)
        op = float(open_price)
        cp = float(close_price)
        if not (lp <= op <= hp and lp <= cp <= hp):
             raise serializers.ValidationError(f"OHLCV prices are inconsistent: L:{lp} O:{op} H:{hp} C:{cp}")

        if high_price < low_price:
            raise serializers.ValidationError({"high": _("High price cannot be less than Low price.")})

        # چک کردن تاریخ‌های باز و بسته
        open_time = attrs.get('open_time')
        close_time = attrs.get('close_time')
        if open_time and close_time and open_time > close_time:
            raise serializers.ValidationError({"close_time": _("Close time cannot be earlier than open time.")})

        return attrs

# --- سایر سریالایزرها ---
# می‌توانید برای سایر مدل‌هایی که در exchanges/models.py تعریف می‌کنید نیز Serializer بنویسید
# مثلاً اگر مدل ExchangeConnectionLog وجود داشت:
# class ExchangeConnectionLogSerializer(CoreBaseSerializer):
#     class Meta(CoreBaseSerializer.Meta):
#         model = ExchangeConnectionLog
#         fields = CoreBaseSerializer.Meta.fields + ['exchange_account', 'status', 'reason', 'connected_at', 'disconnected_at']

logger.info("Exchanges serializers loaded successfully.")
