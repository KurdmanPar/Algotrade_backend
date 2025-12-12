# apps/instruments/serializers.py

from rest_framework import serializers
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from decimal import Decimal
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
from apps.exchanges.models import Exchange # اطمینان از وجود مدل Exchange
from apps.core.helpers import validate_ip_list # import از core برای اعتبارسنجی IP
from apps.core.serializers import CoreOwnedModelSerializer # ارث‌بری از سریالایزر پایه از core
import logging

logger = logging.getLogger(__name__)

class InstrumentGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentGroup
        fields = '__all__'


class InstrumentCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InstrumentCategory
        fields = '__all__'


class InstrumentSerializer(serializers.ModelSerializer):
    # افزودن فیلد برای نمایش نام گروه و دسته
    group_name = serializers.CharField(source='group.name', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = Instrument
        fields = [
            'id', 'symbol', 'name', 'group', 'group_name', 'category', 'category_name',
            'base_asset', 'quote_asset', 'tick_size', 'lot_size', 'is_active',
            'launch_date', 'delisting_date', 'metadata', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at', 'launch_date', 'delisting_date')

    def validate_symbol(self, value):
        """
        Validates the uniqueness of the symbol (case-insensitive).
        Note: The constraint is also defined in the model.
        """
        if Instrument.objects.filter(symbol__iexact=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("An instrument with this symbol already exists.")
        return value

    def validate(self, attrs):
        """
        Custom validation for instrument properties.
        e.g., base_asset and quote_asset cannot be the same.
        """
        base_asset = attrs.get('base_asset', '').upper()
        quote_asset = attrs.get('quote_asset', '').upper()
        if base_asset and quote_asset and base_asset == quote_asset:
            raise serializers.ValidationError("Base asset and quote asset cannot be the same.")

        tick_size = attrs.get('tick_size')
        lot_size = attrs.get('lot_size')

        if tick_size is not None and tick_size <= 0:
            raise serializers.ValidationError({"tick_size": "Tick size must be positive."})
        if lot_size is not None and lot_size <= 0:
            raise serializers.ValidationError({"lot_size": "Lot size must be positive."})

        # اعتبارسنجی دقت اعشاری (مثلاً با استفاده از تابع کمکی از helpers)
        # from apps.core.utils import validate_decimal_precision
        # if tick_size and not validate_decimal_precision(tick_size, max_digits=32, decimal_places=16):
        #     raise serializers.ValidationError({"tick_size": "Tick size precision is invalid."})

        return attrs


class InstrumentExchangeMapSerializer(serializers.ModelSerializer):
    exchange_name = serializers.CharField(source='exchange.name', read_only=True)
    instrument_symbol = serializers.CharField(source='instrument.symbol', read_only=True)
    # فرض بر این است که نماد در صرافی یک فیلد جداگانه است، نه همان نماد اصلی
    # exchange_symbol = serializers.CharField(max_length=64, required=True) # اگر قبلاً در مدل این فیلد وجود نداشت، باید اضافه شود

    class Meta:
        model = InstrumentExchangeMap
        fields = [
            'id', 'instrument', 'instrument_symbol', 'exchange', 'exchange_name', 'exchange_symbol',
            'tick_size', 'lot_size', 'min_notional', 'max_notional', 'min_lot_size', 'max_lot_size',
            'is_active', 'is_margin_enabled', 'is_funding_enabled',
            'max_leverage', 'initial_margin_ratio', 'maintenance_margin_ratio',
            'listing_date', 'delisting_date', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        """
        Custom validation for exchange-specific properties.
        e.g., min_notional should not be greater than max_notional.
        """
        min_notional = attrs.get('min_notional')
        max_notional = attrs.get('max_notional')
        min_lot_size = attrs.get('min_lot_size')
        max_lot_size = attrs.get('max_lot_size')

        if min_notional is not None and max_notional is not None and min_notional > max_notional:
            raise serializers.ValidationError("Min notional cannot be greater than max notional.")

        if min_lot_size is not None and max_lot_size is not None and min_lot_size > max_lot_size:
            raise serializers.ValidationError("Min lot size cannot be greater than max lot size.")

        tick_size = attrs.get('tick_size')
        lot_size = attrs.get('lot_size')

        if tick_size is not None and tick_size <= 0:
            raise serializers.ValidationError({"tick_size": "Exchange tick size must be positive."})
        if lot_size is not None and lot_size <= 0:
            raise serializers.ValidationError({"lot_size": "Exchange lot size must be positive."})

        max_leverage = attrs.get('max_leverage')
        if max_leverage is not None and max_leverage < 1:
            raise serializers.ValidationError({"max_leverage": "Max leverage must be at least 1."})

        initial_mr = attrs.get('initial_margin_ratio')
        maint_mr = attrs.get('maintenance_margin_ratio')
        if initial_mr is not None and maint_mr is not None and initial_mr < maint_mr:
            raise serializers.ValidationError("Initial margin ratio cannot be less than maintenance margin ratio.")

        return attrs


class IndicatorGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorGroup
        fields = '__all__'


class IndicatorSerializer(serializers.ModelSerializer):
    # افزودن نام گروه به خروجی
    group_name = serializers.CharField(source='group.name', read_only=True)

    class Meta:
        model = Indicator
        fields = [
            'id', 'name', 'code', 'group', 'group_name', 'description',
            'is_active', 'is_builtin', 'version', 'calculation_frequency', 'requires_price_data',
            'output_types', 'created_at', 'updated_at'
        ]
        read_only_fields = ('created_at', 'updated_at', 'version')

    def validate_code(self, value):
        """
        Validates the uniqueness of the indicator code (case-insensitive).
        """
        if Indicator.objects.filter(code__iexact=value).exclude(pk=self.instance.pk if self.instance else None).exists():
            raise serializers.ValidationError("An indicator with this code already exists.")
        return value

    def validate_output_types(self, value):
        """
        Validates the structure of the output_types JSON field.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError("Output types must be a list.")
        allowed_types = ['line', 'histogram', 'signal', 'text', 'value'] # مثال
        for ot in value:
            if not isinstance(ot, str) or ot not in allowed_types:
                raise serializers.ValidationError(f"Invalid output type: {ot}. Must be one of {allowed_types}.")
        return value


class IndicatorParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = IndicatorParameter
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')

    def validate(self, attrs):
        """
        Custom validation for parameter constraints.
        e.g., min_value should not be greater than max_value.
        """
        name = attrs.get('name')
        data_type = attrs.get('data_type')
        default_val_str = attrs.get('default_value')
        min_val_str = attrs.get('min_value')
        max_val_str = attrs.get('max_value')
        choices_str = attrs.get('choices')

        # چک کردن تضاد نوع داده و مقدار پیش‌فرض
        if default_val_str:
            self._validate_value_against_type(default_val_str, data_type, f"Default value for parameter '{name}'")

        if min_val_str and max_val_str:
            min_val = self._parse_value_for_type(min_val_str, data_type)
            max_val = self._parse_value_for_type(max_val_str, data_type)
            if min_val is not None and max_val is not None and min_val > max_val:
                raise serializers.ValidationError("Min value cannot be greater than max value.")

        # چک کردن تضاد نوع داده و choices
        if choices_str and data_type != 'choice':
            raise serializers.ValidationError(f"Choices are only allowed for 'choice' data type. Current type is '{data_type}'.")

        if choices_str and data_type == 'choice':
            choices_list = [choice.strip() for choice in choices_str.split(',')]
            for choice_val in choices_list:
                self._validate_value_against_type(choice_val, data_type, f"Choice '{choice_val}' for parameter '{name}'")

        return attrs

    def _parse_value_for_type(self, value_str: str, data_type: str):
        """Attempts to parse a string value based on its declared data_type."""
        try:
            if data_type == 'int':
                return int(value_str)
            elif data_type == 'float':
                return float(value_str)
            elif data_type == 'bool':
                return value_str.lower() in ['true', '1', 'yes', 'on']
            elif data_type == 'str':
                return str(value_str)
            elif data_type == 'choice':
                # choices یک رشته است، باید در validate جداگانه چک شود
                return value_str
            else:
                return value_str # یا None یا ایجاد یک استثنا
        except (ValueError, TypeError):
            return None

    def _validate_value_against_type(self, value_str: str, data_type: str, field_desc: str):
        """Validates a string value against its declared data_type."""
        if data_type == 'int':
            try:
                int(value_str)
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"{field_desc} must be a valid integer for data type 'int'.")
        elif data_type == 'float':
            try:
                float(value_str)
            except (ValueError, TypeError):
                raise serializers.ValidationError(f"{field_desc} must be a valid float for data type 'float'.")
        elif data_type == 'bool':
            if value_str.lower() not in ['true', 'false', '1', '0']:
                raise serializers.ValidationError(f"{field_desc} must be 'true', 'false', '1', or '0' for data type 'bool'.")
        elif data_type == 'str':
            # هر رشته‌ای برای نوع رشته معتبر است، اما ممکن است نیاز به چک‌های دیگری داشته باشید
            pass
        elif data_type == 'choice':
            # اینجا نمی‌توانیم چک کنیم مگر اینکه choices از قبل تعریف شده باشد و در validated_data موجود باشد
            # این چک معمولاً در validate اصلی انجام می‌شود
            pass
        else:
            # می‌توانید خطایی صادر کنید یا فقط چک کنید که مقدار یک رشته است
            pass # یا raise serializers.ValidationError(f"Unknown data type '{data_type}' for {field_desc}.")


class IndicatorTemplateSerializer(serializers.ModelSerializer):
    # ارث‌بری از CoreOwnedModelSerializer اگر فیلد owner داشته باشد
    # owner_username = serializers.CharField(source='owner.username', read_only=True)

    class Meta:
        model = IndicatorTemplate
        fields = [
            'id', 'name', 'description', 'indicator', 'parameters',
            'is_active', 'owner', 'created_at', 'updated_at' # اضافه کردن owner اگر وجود داشته باشد
        ]
        read_only_fields = ('id', 'created_at', 'updated_at', 'owner') # owner فقط در ایجاد تنظیم می‌شود

    def validate_parameters(self, value):
        """
        Validates the structure of the parameters JSON against the indicator's expected parameters.
        This is a complex validation and might require fetching the related Indicator.
        """
        if not isinstance(value, dict):
            raise serializers.ValidationError("Parameters must be a valid JSON object.")

        # این بخش نیازمند دسترسی به Indicator مرتبط است که در زمان create/update وجود دارد
        # در validate یا create/update می‌توان این کار را کرد
        # برای مثال ساده، فقط چک می‌کنیم که مقدار یک دیکشنری است.
        # بررسی محتوای دیکشنری در create یا update انجام می‌شود
        return value

    def create(self, validated_data):
        """
        Override create to set the owner from the request context.
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['owner'] = request.user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """
        Override update to prevent changing the owner.
        """
        validated_data.pop('owner', None) # حذف owner از validated_data
        return super().update(instance, validated_data)

    def validate(self, attrs):
        """
        Validates parameters against the selected indicator's defined parameters.
        """
        # فقط زمانی که indicator و parameters تعریف شده باشند
        indicator = attrs.get('indicator') or (self.instance.indicator if self.instance else None)
        parameters = attrs.get('parameters') or (self.instance.parameters if self.instance else {})

        if not indicator or not isinstance(parameters, dict):
            return attrs # اگر اطلاعات کافی نبود، چک نکن

        try:
            # گرفتن پارامترهای تعریف شده برای این اندیکاتور
            defined_params = {p.name: p for p in indicator.parameters.all()}

            for param_name, param_value in parameters.items():
                if param_name not in defined_params:
                    raise serializers.ValidationError(f"Parameter '{param_name}' is not defined for indicator '{indicator.code}'.")

                expected_type = defined_params[param_name].data_type
                # چک کردن نوع داده مقدار ورودی با نوع تعریف شده
                # این بخش می‌تواند پیچیده شود بسته به نحوه ذخیره و تفسیر مقدارها
                # مثال ساده:
                if expected_type == 'int':
                    if not isinstance(param_value, int):
                        raise serializers.ValidationError(f"Parameter '{param_name}' expects an integer value.")
                elif expected_type == 'float':
                    if not isinstance(param_value, (int, float)):
                        raise serializers.ValidationError(f"Parameter '{param_name}' expects a float value.")
                elif expected_type == 'bool':
                    if not isinstance(param_value, bool):
                        raise serializers.ValidationError(f"Parameter '{param_name}' expects a boolean value.")
                elif expected_type == 'str':
                    if not isinstance(param_value, str):
                        raise serializers.ValidationError(f"Parameter '{param_name}' expects a string value.")
                # برای 'choice' نیز چک کنید:
                elif expected_type == 'choice':
                    choices_str = defined_params[param_name].choices
                    if choices_str:
                        allowed_choices = [choice.strip() for choice in choices_str.split(',')]
                        if param_value not in allowed_choices:
                            raise serializers.ValidationError(f"Parameter '{param_name}' value '{param_value}' is not in allowed choices: {allowed_choices}.")

        except Exception as e:
            logger.error(f"Error validating template parameters against indicator {indicator.code if indicator else 'N/A'}: {str(e)}")
            raise serializers.ValidationError(f"Parameter validation failed: {str(e)}")

        return attrs


class PriceActionPatternSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceActionPattern
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class SmartMoneyConceptSerializer(serializers.ModelSerializer):
    class Meta:
        model = SmartMoneyConcept
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class AIMetricSerializer(serializers.ModelSerializer):
    class Meta:
        model = AIMetric
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')


class InstrumentWatchlistSerializer(CoreOwnedModelSerializer): # ارث‌بری از CoreOwnedModelSerializer
    """
    Serializer for the InstrumentWatchlist model.
    Uses CoreOwnedModelSerializer for common owner logic.
    """
    # Nested serialization for instruments if needed in the watchlist
    instruments = InstrumentSerializer(many=True, read_only=True)
    # Or just show IDs if only linking is needed
    # instrument_ids = serializers.PrimaryKeyRelatedField(queryset=Instrument.objects.all(), many=True, write_only=True)

    class Meta(CoreOwnedModelSerializer.Meta): # ارث‌بری از Meta CoreOwnedModelSerializer
        model = InstrumentWatchlist
        fields = CoreOwnedModelSerializer.Meta.fields + [ # افزودن فیلدهای خاص Watchlist
            'name', 'description', 'is_public', 'instruments'
        ]
        # read_only_fields = CoreOwnedModelSerializer.Meta.read_only_fields + ('created_at', 'updated_at')

    # نیازی به تعریف مجدد create/update نیست، زیرا CoreOwnedModelSerializer این کار را انجام می‌دهد
    # def create(self, validated_data):
    #     request = self.context.get('request')
    #     if request and hasattr(request, 'user'):
    #         validated_data['owner'] = request.user
    #     return super().create(validated_data)
    #
    # def update(self, instance, validated_data):
    #     validated_data.pop('owner', None) # جلوگیری از تغییر owner
    #     return super().update(instance, validated_data)

    def validate(self, attrs):
        """
        Custom validation for the watchlist.
        e.g., prevent duplicate instruments in the same watchlist (handled by M2M uniqueness usually, but can be checked here too).
        """
        # این چک معمولاً در سطح مدل (constraint) یا در M2M signal انجام می‌شود
        # برای مثال، فقط چک می‌کنیم که نام لیست منحصر به فرد باشد برای هر کاربر
        name = attrs.get('name')
        if name and self.instance is None: # فقط در هنگام ایجاد
            owner = self.context['request'].user if 'request' in self.context else self.instance.owner
            if InstrumentWatchlist.objects.filter(owner=owner, name__iexact=name).exists():
                 raise serializers.ValidationError({"name": "A watchlist with this name already exists for you."})
        return attrs

# --- مثال: سریالایزر برای مدل جدید ---
# اگر مدل InstrumentWatchlist در اپلیکیشن instruments تعریف شده بود (نه core)، می‌توانست از CoreOwnedModelSerializer ارث ببرد
# class InstrumentWatchlistSerializer(serializers.ModelSerializer):
#     owner_username = serializers.CharField(source='owner.username', read_only=True)
#     instruments = InstrumentSerializer(many=True, read_only=True)
#     class Meta:
#         model = InstrumentWatchlist
#         fields = ['id', 'name', 'description', 'owner', 'owner_username', 'is_public', 'instruments', 'created_at', 'updated_at']
#         read_only_fields = ['owner', 'created_at', 'updated_at']
#     def create(self, validated_data):
#         request = self.context.get('request')
#         if request and hasattr(request, 'user'):
#             validated_data['owner'] = request.user
#         return super().create(validated_data)
#     def update(self, instance, validated_data):
#         validated_data.pop('owner', None)
#         return super().update(instance, validated_data)
