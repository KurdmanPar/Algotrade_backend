# apps/instruments/services.py

from typing import Dict, List, Optional, Any
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings
import logging
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
from .exceptions import (
    InstrumentValidationError,
    DataSyncError,
    IndicatorValidationError,
    # سایر استثناهای سفارشی شما
)
from .helpers import (
    validate_ip_list,
    is_ip_in_allowed_list,
    normalize_data_from_source,
    validate_ohlcv_data,
    # سایر توابع کمکی شما
)
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویس وجود دارد
from apps.core.logging import get_logger # فرض بر این است که یک سیستم لاگ مرکزی دارید

logger = get_logger(__name__)

class InstrumentService:
    """
    Service class for handling instrument-related business logic.
    This includes creation, updates, exchange mapping, and interactions with data connectors.
    """

    @staticmethod
    def create_instrument_with_mappings(
        symbol: str,
        name: str,
        group_id: int,
        category_id: int,
        base_asset: str,
        quote_asset: str,
        tick_size: Decimal,
        lot_size: Decimal,
        exchange_mappings_data: List[Dict[str, Any]]
    ) -> Instrument:
        """
        Creates an instrument and its exchange-specific mappings within a database transaction.
        Args:
            symbol: The universal symbol (e.g., BTCUSDT).
            name: The full name (e.g., Bitcoin / Tether).
            group_id: ID of the InstrumentGroup.
            category_id: ID of the InstrumentCategory.
            base_asset: The base currency (e.g., BTC).
            quote_asset: The quote currency (e.g., USDT).
            tick_size: Global tick size.
            lot_size: Global lot size.
            exchange_mappings_data: A list of dicts containing exchange-specific data.
                                    e.g., [{"exchange_id": 1, "exchange_symbol": "BTCUSDT", "tick_size": "0.01", ...}, ...]
        Returns:
            The created Instrument object.
        Raises:
            InstrumentValidationError: If any validation fails.
            IntegrityError: If a unique constraint is violated (e.g., duplicate symbol).
        """
        try:
            with transaction.atomic():
                # 1. Create the main instrument
                instrument = Instrument.objects.create(
                    symbol=symbol,
                    name=name,
                    group_id=group_id,
                    category_id=category_id,
                    base_asset=base_asset,
                    quote_asset=quote_asset,
                    tick_size=tick_size,
                    lot_size=lot_size,
                    is_active=True,
                )
                logger.info(f"Created instrument {instrument.symbol}.")

                # 2. Create exchange mappings
                for map_data in exchange_mappings_data:
                    exchange_id = map_data.get('exchange_id')
                    exchange_symbol = map_data.get('exchange_symbol')
                    ex_tick_size = Decimal(str(map_data.get('tick_size', tick_size))) # Default to global
                    ex_lot_size = Decimal(str(map_data.get('lot_size', lot_size))) # Default to global
                    min_notional = Decimal(str(map_data.get('min_notional', 0)))
                    max_notional = map_data.get('max_notional')
                    is_active_map = map_data.get('is_active', True)

                    InstrumentExchangeMap.objects.create(
                        instrument=instrument,
                        exchange_id=exchange_id,
                        exchange_symbol=exchange_symbol,
                        tick_size=ex_tick_size,
                        lot_size=ex_lot_size,
                        min_notional=min_notional,
                        max_notional=Decimal(max_notional) if max_notional else None,
                        is_active=is_active_map,
                    )
                    logger.info(f"Created exchange map for {instrument.symbol} on exchange ID {exchange_id}.")

                return instrument

        except IntegrityError as e:
            logger.error(f"Integrity error creating instrument {symbol}: {str(e)}")
            raise InstrumentValidationError(f"Failed to create instrument {symbol}. It might already exist.") from e
        except ValidationError as e:
            logger.error(f"Validation error creating instrument {symbol}: {str(e)}")
            raise InstrumentValidationError(f"Validation failed for instrument {symbol}: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error creating instrument {symbol} with mappings: {str(e)}")
            # بسته به نیاز، می‌توانید یک استثنا جدید یا استثنا پایه‌ای را دوباره بالا بیاورید
            raise CoreServiceError(f"An unexpected error occurred while creating instrument {symbol}: {str(e)}") from e

    @staticmethod
    def update_instrument_metadata(instrument_id: int, metadata_updates: Dict[str, Any]) -> Instrument:
        """
        Updates the metadata JSON field of an instrument.
        This is useful for storing dynamic properties fetched from exchanges or calculated offline.
        """
        try:
            instrument = Instrument.objects.get(id=instrument_id)
            current_metadata = instrument.metadata or {}
            current_metadata.update(metadata_updates)
            instrument.metadata = current_metadata
            instrument.save(update_fields=['metadata'])
            logger.info(f"Updated metadata for instrument ID {instrument_id}.")
            return instrument
        except Instrument.DoesNotExist:
            logger.error(f"Attempted to update metadata for non-existent instrument ID {instrument_id}.")
            raise InstrumentNotFound(f"Instrument with ID {instrument_id} not found.")
        except Exception as e:
            logger.error(f"Error updating metadata for instrument ID {instrument_id}: {str(e)}")
            raise CoreServiceError(f"Failed to update metadata for instrument ID {instrument_id}: {str(e)}")

    @staticmethod
    def sync_instrument_details_from_exchange(instrument_id: int, exchange_id: int) -> bool:
        """
        Fetches the latest instrument details (like limits, fees, status) from a specific exchange
        and updates the corresponding InstrumentExchangeMap.
        This requires interaction with the ConnectorService.
        """
        try:
            instrument = Instrument.objects.get(id=instrument_id)
            exchange_map = InstrumentExchangeMap.objects.get(instrument=instrument, exchange_id=exchange_id)

            connector = ConnectorService(exchange_map.exchange.name)
            # فرض بر این است که کانکتور متدی برای گرفتن اطلاعات نماد خاص دارد
            raw_details = connector.fetch_instrument_details(exchange_map.exchange_symbol)

            # مثال: به‌روزرسانی فیلدهای خاص
            exchange_map.tick_size = Decimal(str(raw_details.get('tickSize', exchange_map.tick_size)))
            exchange_map.lot_size = Decimal(str(raw_details.get('lotSize', exchange_map.lot_size)))
            exchange_map.min_notional = Decimal(str(raw_details.get('minNotional', exchange_map.min_notional)))
            exchange_map.max_notional = Decimal(str(raw_details.get('maxNotional'))) if raw_details.get('maxNotional') else None
            exchange_map.is_active = raw_details.get('status') == 'TRADING' # فرض بر این است که وضعیت صرافی این گونه تعریف شده
            exchange_map.save(update_fields=['tick_size', 'lot_size', 'min_notional', 'max_notional', 'is_active'])

            logger.info(f"Synced details for instrument {instrument.symbol} on exchange {exchange_map.exchange.name}.")
            return True

        except Instrument.DoesNotExist:
            logger.error(f"Instrument with ID {instrument_id} not found for sync.")
            raise InstrumentNotFound(f"Instrument with ID {instrument_id} not found.")
        except InstrumentExchangeMap.DoesNotExist:
            logger.error(f"InstrumentExchangeMap for instrument ID {instrument_id} and exchange ID {exchange_id} not found.")
            raise InstrumentExchangeMapError(f"Mapping for instrument ID {instrument_id} and exchange ID {exchange_id} not found.")
        except Exception as e:
            logger.error(f"Error syncing details for instrument {instrument_id} on exchange {exchange_id}: {str(e)}")
            raise CoreServiceError(f"Failed to sync details from exchange: {str(e)}")


    @staticmethod
    def get_instruments_for_exchange(exchange_id: int, active_only: bool = True) -> List[Instrument]:
        """
        Retrieves all instruments mapped to a specific exchange.
        Optionally filters for active instruments only.
        """
        try:
            mappings = InstrumentExchangeMap.objects.filter(
                exchange_id=exchange_id
            )
            if active_only:
                 mappings = mappings.filter(is_active=True)

            instrument_ids = mappings.values_list('instrument_id', flat=True)
            instruments = Instrument.objects.filter(id__in=instrument_ids)

            if active_only:
                instruments = instruments.filter(is_active=True)

            logger.debug(f"Fetched {instruments.count()} instruments for exchange ID {exchange_id}.")
            return instruments
        except Exception as e:
            logger.error(f"Error fetching instruments for exchange ID {exchange_id}: {str(e)}")
            raise CoreServiceError(f"Failed to fetch instruments for exchange: {str(e)}")

    # --- سایر متدهای مرتبط با Instrument ---
    # مثلاً:
    # def get_active_instruments_by_group(self, group_id):
    #     ...
    # def search_instruments(self, query):
    #     ...


class IndicatorService:
    """
    Service class for handling business logic related to Indicators, Parameters, and Templates.
    """
    @staticmethod
    def create_indicator_with_params(name: str, code: str, group_id: int, parameters_data: List[Dict[str, Any]]) -> Indicator:
        """
        Creates an indicator along with its associated parameters.
        """
        try:
            with transaction.atomic():
                indicator = Indicator.objects.create(
                    name=name,
                    code=code,
                    group_id=group_id,
                    is_active=True,
                    is_builtin=False # اندیکاتورهای سفارشی غیر داخلی هستند
                )
                logger.info(f"Created indicator {indicator.code}.")

                for param_data in parameters_data:
                    IndicatorParameter.objects.create(
                        indicator=indicator,
                        name=param_data['name'],
                        display_name=param_data['display_name'],
                        data_type=param_data['data_type'],
                        default_value=param_data.get('default_value'),
                        min_value=param_data.get('min_value'),
                        max_value=param_data.get('max_value'),
                        choices=param_data.get('choices', '')
                    )
                logger.info(f"Created parameters for indicator {indicator.code}.")
                return indicator
        except IntegrityError as e:
            logger.error(f"Integrity error creating indicator {code}: {str(e)}")
            raise IndicatorValidationError(f"Indicator with code {code} already exists.") from e
        except Exception as e:
            logger.error(f"Unexpected error creating indicator {code} with params: {str(e)}")
            raise CoreServiceError(f"Failed to create indicator {code}: {str(e)}")

    @staticmethod
    def validate_indicator_template_parameters(template_id: int, user_provided_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates user-provided parameters against the defined parameters of an indicator template.
        Ensures types and ranges are correct.
        Returns the validated and potentially type-converted parameters.
        Raises IndicatorValidationError if validation fails.
        """
        try:
            template = IndicatorTemplate.objects.select_related('indicator').prefetch_related('indicator__parameters').get(id=template_id)
            defined_params = template.indicator.parameters.all()

            validated_params = {}
            for param_def in defined_params:
                param_name = param_def.name
                user_value_str = user_provided_params.get(param_name)

                if user_value_str is None:
                    # Check if there's a default value
                    if param_def.default_value:
                        user_value_str = param_def.default_value
                    else:
                        raise IndicatorValidationError(f"Required parameter '{param_name}' is missing.")

                # Convert and validate based on data_type
                if param_def.data_type == 'int':
                    try:
                        validated_value = int(user_value_str)
                    except (ValueError, TypeError):
                        raise IndicatorValidationError(f"Parameter '{param_name}' must be an integer.")
                    if param_def.min_value is not None and validated_value < int(param_def.min_value):
                         raise IndicatorValidationError(f"Parameter '{param_name}' must be >= {param_def.min_value}.")
                    if param_def.max_value is not None and validated_value > int(param_def.max_value):
                         raise IndicatorValidationError(f"Parameter '{param_name}' must be <= {param_def.max_value}.")
                elif param_def.data_type == 'float':
                    try:
                        validated_value = float(user_value_str)
                    except (ValueError, TypeError):
                        raise IndicatorValidationError(f"Parameter '{param_name}' must be a float.")
                    # Apply min/max validation for floats similarly
                    if param_def.min_value is not None:
                        min_val_float = float(param_def.min_value)
                        if validated_value < min_val_float:
                            raise IndicatorValidationError(f"Parameter '{param_name}' must be >= {min_val_float}.")
                    if param_def.max_value is not None:
                        max_val_float = float(param_def.max_value)
                        if validated_value > max_val_float:
                            raise IndicatorValidationError(f"Parameter '{param_name}' must be <= {max_val_float}.")
                elif param_def.data_type == 'bool':
                    if isinstance(user_value_str, str):
                        validated_value = user_value_str.lower() in ['true', '1', 'yes', 'on']
                    else:
                        validated_value = bool(user_value_str)
                elif param_def.data_type == 'str':
                    validated_value = str(user_value_str)
                    if param_def.choices:
                        allowed_choices = [choice.strip() for choice in param_def.choices.split(',')]
                        if validated_value not in allowed_choices:
                            raise IndicatorValidationError(f"Parameter '{param_name}' value '{validated_value}' is not in allowed choices: {allowed_choices}.")
                else:
                    # Handle other data types if necessary
                    validated_value = user_value_str # Default, might need stricter handling

                validated_params[param_name] = validated_value

            logger.debug(f"Validated parameters for template ID {template_id}.")
            return validated_params

        except IndicatorTemplate.DoesNotExist:
            logger.error(f"IndicatorTemplate with ID {template_id} not found for validation.")
            raise IndicatorValidationError(f"Indicator template with ID {template_id} not found.")
        except Exception as e:
            logger.error(f"Error validating parameters for template ID {template_id}: {str(e)}")
            raise IndicatorValidationError(f"Parameter validation failed: {str(e)}")

    # --- سایر متدهای مرتبط با Indicator ---
    # مثلاً:
    # def get_active_indicators_by_group(self, group_id):
    #     ...
    # def apply_indicator_to_data(self, indicator_id, data, params):
    #     ... (این ممکن است در یک سرویس تحلیلی جداگانه باشد)


class WatchlistService:
    """
    Service class for handling business logic related to InstrumentWatchlists.
    """
    @staticmethod
    def create_watchlist_for_user(owner_user, name: str, description: str = "", is_public: bool = False) -> InstrumentWatchlist:
        """
        Creates a new watchlist owned by a specific user.
        """
        try:
            watchlist = InstrumentWatchlist.objects.create(
                name=name,
                description=description,
                owner=owner_user,
                is_public=is_public
            )
            logger.info(f"Created watchlist '{name}' for user {owner_user.username}.")
            return watchlist
        except IntegrityError as e:
            logger.error(f"Integrity error creating watchlist '{name}' for user {owner_user.username}: {str(e)}")
            raise WatchlistError(f"A watchlist with the name '{name}' already exists for this user.") from e
        except Exception as e:
            logger.error(f"Unexpected error creating watchlist '{name}' for user {owner_user.username}: {str(e)}")
            raise CoreServiceError(f"Failed to create watchlist: {str(e)}")

    @staticmethod
    def add_instrument_to_watchlist(watchlist_id: int, user, instrument_id: int) -> bool:
        """
        Adds an instrument to a watchlist, ensuring the user owns the watchlist.
        """
        try:
            watchlist = InstrumentWatchlist.objects.get(id=watchlist_id)
            if watchlist.owner != user:
                logger.warning(f"User {user.username} tried to modify watchlist {watchlist.name} owned by {watchlist.owner.username}.")
                raise WatchlistOwnershipError("You do not own this watchlist.")
            instrument = Instrument.objects.get(id=instrument_id)

            # استفاده از add برای M2M - اگر قبلاً وجود نداشته باشد، اضافه می‌شود
            watchlist.instruments.add(instrument)
            logger.info(f"Added instrument {instrument.symbol} to watchlist {watchlist.name}.")
            return True
        except InstrumentWatchlist.DoesNotExist:
            logger.error(f"Watchlist with ID {watchlist_id} not found.")
            raise WatchlistError("Watchlist not found.")
        except Instrument.DoesNotExist:
            logger.error(f"Instrument with ID {instrument_id} not found.")
            raise WatchlistError("Instrument not found.")
        except WatchlistOwnershipError:
            # این استثنا قبلاً بالا آورده شده است
            raise
        except Exception as e:
            logger.error(f"Error adding instrument to watchlist {watchlist_id}: {str(e)}")
            raise CoreServiceError(f"Failed to add instrument to watchlist: {str(e)}")

    @staticmethod
    def get_watchlists_for_user_or_public(user) -> List[InstrumentWatchlist]:
        """
        Retrieves watchlists owned by the user or public watchlists.
        """
        try:
            # نمایش لیست‌های مالک و لیست‌های عمومی
            watchlists = InstrumentWatchlist.objects.filter(
                models.Q(owner=user) | models.Q(is_public=True)
            ).distinct() # اطمینان از عدم تکرار
            logger.debug(f"Fetched {watchlists.count()} watchlists for user {user.username} or public.")
            return watchlists
        except Exception as e:
            logger.error(f"Error fetching watchlists for user {user.username}: {str(e)}")
            raise CoreServiceError(f"Failed to fetch watchlists: {str(e)}")

    # --- سایر متدهای مرتبط با Watchlist ---
    # مثلاً:
    # def remove_instrument_from_watchlist(self, watchlist_id, user, instrument_id):
    #     ...
    # def get_instruments_from_watchlist(self, watchlist_id, user):
    #     ...


# --- سایر سرویس‌های مرتبط ---
# مثلاً یک سرویس برای مدیریت الگوهای اکشن قیمت یا مفاهیم اسمارت مانی
# class PriceActionService:
#     ...

# class SmartMoneyConceptService:
#     ...

# class AIMetricService:
#     ...
