# apps/instruments/managers.py

from django.db import models
from django.utils import timezone
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

class InstrumentQuerySet(models.QuerySet):
    """
    Custom QuerySet for the Instrument model.
    Provides methods for filtering and aggregating instrument data efficiently.
    """

    def active(self):
        """
        Filters for instruments that are currently active and not delisted.
        """
        now = timezone.now()
        return self.filter(
            is_active=True,
            delisting_date__isnull=True # یا delisting_date__gt=now اگر تاریخ واقعاً مهم باشد
        )

    def by_group(self, group_id_or_name):
        """
        Filters instruments by their group.
        Accepts either the group's ID or its name.
        """
        if isinstance(group_id_or_name, int):
            return self.filter(group_id=group_id_or_name)
        else:
            return self.filter(group__name__iexact=group_id_or_name)

    def by_category(self, category_id_or_name):
        """
        Filters instruments by their category.
        Accepts either the category's ID or its name.
        """
        if isinstance(category_id_or_name, int):
            return self.filter(category_id=category_id_or_name)
        else:
            return self.filter(category__name__iexact=category_id_or_name)

    def by_symbol(self, symbol):
        """
        Filters instruments by their exact symbol (case-insensitive).
        """
        return self.filter(symbol__iexact=symbol)

    def by_base_asset(self, asset):
        """
        Filters instruments by their base asset (e.g., 'BTC').
        """
        return self.filter(base_asset__iexact=asset)

    def by_quote_asset(self, asset):
        """
        Filters instruments by their quote asset (e.g., 'USDT').
        """
        return self.filter(quote_asset__iexact=asset)

    def for_exchange(self, exchange_id_or_name):
        """
        Filters instruments that are mapped to a specific exchange.
        Joins with InstrumentExchangeMap model.
        """
        return self.filter(exchange_mappings__exchange_id=exchange_id_or_name, exchange_mappings__is_active=True)

    def with_min_volume(self, volume_threshold: Decimal):
        """
        Filters instruments based on a minimum 24h volume threshold (requires a volume field on Instrument or via annotation).
        Note: This assumes a 'volume_24h' field exists or will be annotated later.
        """
        # این فیلتر فقط کار می‌کند اگر 'volume_24h' در مدل یا از طریق annotate اضافه شده باشد.
        return self.filter(volume_24h__gte=volume_threshold)

    def search(self, query):
        """
        Searches for instruments by symbol or name.
        """
        if not query:
            return self.none()
        return self.filter(Q(symbol__icontains=query) | Q(name__icontains=query))

    def with_metadata_contains(self, key, value=None):
        """
        Filters instruments where the metadata JSON field contains a specific key/value pair.
        If 'value' is None, only checks for the existence of the key.
        """
        if value is not None:
            return self.filter(metadata__contains={key: value})
        else:
            # Django 3.2+ supports this syntax for checking key existence
            # For older versions, you might need a raw SQL expression or a different approach
            return self.filter(metadata__has_key=key)

    # --- منطق جدید مرتبط با نمادها ---
    def futures_contracts(self):
        """
        Filters instruments that are futures contracts (based on category).
        """
        return self.filter(category__name__iexact='futures')

    def perpetual_contracts(self):
        """
        Filters instruments that are perpetual contracts (based on category).
        """
        return self.filter(category__name__iexact='perpetual')

    def spot_pairs(self):
        """
        Filters instruments that are spot pairs (based on category).
        """
        return self.filter(category__name__iexact='spot')

    def with_leverage(self):
        """
        Filters instruments that support leverage (based on category or metadata).
        """
        # فرض بر این است که دسته یا متادیتا نشان می‌دهد
        return self.filter(category__supports_leverage=True) # فرض بر این است که فیلد وجود دارد

    def with_minimum_tick_size(self, min_tick: Decimal):
        """
        Filters instruments with a tick size greater than or equal to a minimum value.
        """
        return self.filter(tick_size__gte=min_tick)

    def with_minimum_lot_size(self, min_lot: Decimal):
        """
        Filters instruments with a lot size greater than or equal to a minimum value.
        """
        return self.filter(lot_size__gte=min_lot)

    # --- منطق مرتبط با InstrumentExchangeMap ---
    def with_active_mapping_on_exchange(self, exchange_id_or_name):
        """
        Filters instruments that have an *active* mapping to a specific exchange.
        """
        return self.filter(exchange_mappings__exchange_id=exchange_id_or_name, exchange_mappings__is_active=True).distinct()


class InstrumentManager(models.Manager):
    """
    Custom Manager for the Instrument model.
    Uses the custom InstrumentQuerySet.
    """
    def get_queryset(self):
        return InstrumentQuerySet(self.model, using=self._db)

    # می‌توانید متد‌هایی که فقط یک شیء برمی‌گردانند یا منطق خاصی دارند را اینجا تعریف کنید
    # مثلاً:
    # def get_by_symbol_or_raise(self, symbol):
    #     try:
    #         return self.get_queryset().by_symbol(symbol).get()
    #     except self.model.DoesNotExist:
    #         raise SomeCustomException(f"Instrument with symbol {symbol} does not exist.")


class InstrumentExchangeMapQuerySet(models.QuerySet):
    """
    Custom QuerySet for InstrumentExchangeMap model.
    Provides methods for filtering maps based on exchange, instrument, or status.
    """
    def for_exchange(self, exchange_id_or_name):
        """
        Filters maps for a specific exchange.
        """
        if isinstance(exchange_id_or_name, int):
            return self.filter(exchange_id=exchange_id_or_name)
        else:
            return self.filter(exchange__name__iexact=exchange_id_or_name)

    def for_instrument(self, instrument_id_or_symbol):
        """
        Filters maps for a specific instrument.
        """
        if isinstance(instrument_id_or_symbol, int):
            return self.filter(instrument_id=instrument_id_or_symbol)
        else:
            return self.filter(instrument__symbol__iexact=instrument_id_or_symbol)

    def active(self):
        """
        Filters maps that are active on the exchange.
        """
        return self.filter(is_active=True)

    def with_min_notional(self, min_notional: Decimal):
        """
        Filters maps where the exchange-specific min_notional meets a threshold.
        """
        return self.filter(min_notional__gte=min_notional)

    def with_max_leverage_gte(self, leverage: Decimal):
        """
        Filters maps where the exchange-specific max_leverage is greater than or equal to a value.
        """
        return self.filter(max_leverage__gte=leverage)

    def for_active_instruments(self):
        """
        Filters maps where the associated Instrument is also active.
        """
        return self.filter(instrument__is_active=True)

    # --- منطق جدید مرتبط با InstrumentExchangeMap ---
    def with_margin_enabled(self):
        """
        Filters maps where margin trading is enabled on the exchange.
        """
        return self.filter(is_margin_enabled=True)

    def with_funding_enabled(self):
        """
        Filters maps where funding fees apply (relevant for perpetuals).
        """
        return self.filter(is_funding_enabled=True)

    def expiring_soon(self, days_ahead: int = 7):
        """
        Filters maps for instruments that are expiring soon (for futures).
        """
        cutoff_date = timezone.now() + timezone.timedelta(days=days_ahead)
        return self.filter(delisting_date__lte=cutoff_date, delisting_date__isnull=False)


class InstrumentExchangeMapManager(models.Manager):
    """
    Custom Manager for InstrumentExchangeMap model.
    Uses the custom InstrumentExchangeMapQuerySet.
    """
    def get_queryset(self):
        return InstrumentExchangeMapQuerySet(self.model, using=self._db)


class IndicatorQuerySet(models.QuerySet):
    """
    Custom QuerySet for Indicator model.
    Provides methods for filtering indicators.
    """
    def active(self):
        """Filters active indicators."""
        return self.filter(is_active=True)

    def builtin(self):
        """Filters built-in indicators."""
        return self.filter(is_builtin=True)

    def by_group(self, group_id_or_name):
        """Filters by indicator group."""
        if isinstance(group_id_or_name, int):
            return self.filter(group_id=group_id_or_name)
        else:
            return self.filter(group__name__iexact=group_id_or_name)

    def with_name_or_code(self, term):
        """Filters by name or code (case-insensitive)."""
        return self.filter(Q(name__iexact=term) | Q(code__iexact=term))

    # --- منطق جدید مرتبط با اندیکاتورها ---
    def for_trading_strategies(self):
        """
        Filters indicators commonly used in trading strategies (e.g., excluding long-term economic indicators).
        """
        # فرض بر این است که یک فیلد یا دسته‌بندی وجود دارد که این را مشخص می‌کند
        # ممکن است نیاز به یک فیلد دسته‌بندی جدید یا استفاده از متادیتا باشد
        # برای مثال ساده، فقط اکتیو و بیلتین:
        return self.filter(is_active=True, is_builtin=True)


class IndicatorManager(models.Manager):
    """
    Custom Manager for Indicator model.
    Uses the custom IndicatorQuerySet.
    """
    def get_queryset(self):
        return IndicatorQuerySet(self.model, using=self._db)


class IndicatorTemplateQuerySet(models.QuerySet):
    """
    Custom QuerySet for IndicatorTemplate model.
    Provides methods for filtering templates.
    """
    def active(self):
        """Filters active templates."""
        return self.filter(is_active=True)

    def by_indicator(self, indicator_id_or_code):
        """Filters by a specific indicator."""
        if isinstance(indicator_id_or_code, int):
            return self.filter(indicator_id=indicator_id_or_code)
        else:
            return self.filter(indicator__code__iexact=indicator_id_or_code)

    def global_or_owned_by_user(self, user):
        """Filters templates that are global (e.g., is_global=True) or owned by a specific user."""
        # فرض بر این است که مدل دارای فیلدهای is_global و owner است
        return self.filter(Q(is_global=True) | Q(owner=user))


class IndicatorTemplateManager(models.Manager):
    """
    Custom Manager for IndicatorTemplate model.
    Uses the custom IndicatorTemplateQuerySet.
    """
    def get_queryset(self):
        return IndicatorTemplateQuerySet(self.model, using=self._db)


# --- منیجرهای مدل‌های دیگر ---
# می‌توانید برای سایر مدل‌هایی که در instruments/models.py وجود دارند (مثل PriceActionPattern، SmartMoneyConcept، AIMetric، InstrumentWatchlist)
# نیز QuerySet و Manager سفارشی بنویسید.

class PriceActionPatternQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def by_code(self, code):
        return self.filter(code__iexact=code)

class PriceActionPatternManager(models.Manager):
    def get_queryset(self):
        return PriceActionPatternQuerySet(self.model, using=self._db)

class SmartMoneyConceptQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def by_code(self, code):
        return self.filter(code__iexact=code)

class SmartMoneyConceptManager(models.Manager):
    def get_queryset(self):
        return SmartMoneyConceptQuerySet(self.model, using=self._db)

class AIMetricQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def by_code(self, code):
        return self.filter(code__iexact=code)

    def by_data_type(self, data_type):
        return self.filter(data_type__iexact=data_type)

class AIMetricManager(models.Manager):
    def get_queryset(self):
        return AIMetricQuerySet(self.model, using=self._db)

class InstrumentWatchlistQuerySet(models.QuerySet):
    def public(self):
        return self.filter(is_public=True)

    def owned_by(self, user):
        return self.filter(owner=user)

    def containing_instrument(self, instrument_id):
        return self.filter(instruments__id=instrument_id)

class InstrumentWatchlistManager(models.Manager):
    def get_queryset(self):
        return InstrumentWatchlistQuerySet(self.model, using=self._db)
