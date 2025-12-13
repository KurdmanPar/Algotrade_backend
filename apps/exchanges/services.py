# apps/exchanges/services.py

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from django.conf import settings
from .models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    OrderHistory,
    MarketDataCandle,
)
from apps.bots.models import TradingBot # import از اپلیکیشن دیگر
from apps.connectors.service import ConnectorService # import از اپلیکیشن دیگر
from apps.market_data.service import MarketDataService # import از اپلیکیشن دیگر
from apps.core.models import AuditLog # import از اپلیکیشن core
from apps.core.exceptions import (
    CoreSystemException,
    DataIntegrityException,
    SecurityException,
    # سایر استثناهای سطح سیستم
)
from apps.core.helpers import (
    get_client_ip,
    generate_device_fingerprint,
    # سایر توابع کمکی
)
from apps.core.services import (
    CoreService,
    AuditService,
    # سایر سرویس‌های core
)
from .exceptions import (
    ExchangeBaseError,
    ExchangeSyncError,
    DataFetchError,
    OrderExecutionError,
    InvalidCredentialsError,
    InsufficientBalanceError,
    RateLimitExceededError,
    # سایر استثناهای سفارشی exchanges
)
from .helpers import (
    validate_exchange_response,
    normalize_data_from_source,
    validate_ohlcv_data,
    # سایر توابع کمکی exchanges
)

logger = logging.getLogger(__name__)

class ExchangeService:
    """
    Service class for handling exchange-related business logic.
    This includes API communication, data synchronization, and order management.
    """
    def __init__(self):
        # احتمالاً نیاز به یک نمونه از ConnectorService یا MarketDataService دارد
        self.connector_service = ConnectorService()
        self.market_data_service = MarketDataService()

    def sync_exchange_account(self, account: ExchangeAccount) -> dict:
        """
        Synchronizes account info, balances, and orders from the exchange.
        This is a complex operation that involves multiple API calls.
        Uses transactions and error handling.
        """
        try:
            # 1. دریافت اطلاعات حساب از صرافی
            exchange_info = self.connector_service.get_account_info(account)
            validated_info = validate_exchange_response(exchange_info, 'account_info')
            logger.info(f"Fetched account info for {account.label} on {account.exchange.name}")

            # 2. دریافت موجودی‌ها
            balances_raw = self.connector_service.get_account_balances(account)
            validated_balances = validate_exchange_response(balances_raw, 'balances')
            logger.info(f"Fetched {len(validated_balances)} balances for {account.label}")

            # 3. دریافت تاریخچه سفارشات جدید (مثلاً از 24 ساعت گذشته)
            # ممکن است نیاز به فیلتر بر اساس تاریخ آخرین سینک باشد
            last_sync = account.last_sync_at or (timezone.now() - timedelta(days=1))
            orders_raw = self.connector_service.get_account_orders(account, since=last_sync)
            validated_orders = validate_exchange_response(orders_raw, 'orders')
            logger.info(f"Fetched {len(validated_orders)} new orders for {account.label}")

            # 4. به‌روزرسانی مدل‌های پایگاه داده
            # این بخش باید با دقت و در یک تراکنش انجام شود
            with transaction.atomic():
                # به‌روزرسانی اطلاعات حساب
                account.account_info = validated_info
                account.trading_permissions = validated_info.get('permissions', {})
                account.last_sync_at = timezone.now()
                account.save(update_fields=['account_info', 'trading_permissions', 'last_sync_at'])

                # به‌روزرسانی موجودی‌ها
                self._update_balances(account, validated_balances)

                # به‌روزرسانی یا ایجاد تاریخچه سفارشات
                self._update_order_history(account, validated_orders)

            # 5. ثبت لاگ حسابرسی
            AuditService.log_action(
                user=account.owner, # از owner ارث‌برده شده از BaseOwnedModel
                action='ACCOUNT_SYNC_SUCCESS',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={
                    'account_label': account.label,
                    'exchange': account.exchange.name,
                    'balances_synced': len(validated_balances),
                    'orders_synced': len(validated_orders),
                },
                request=None # نداریم، چون از پس‌زمینه (task) فراخوانی می‌شود
            )

            # 6. بازگرداندن اطلاعات همگام‌سازی شده
            return {
                'account_info': validated_info,
                'balances': validated_balances,
                'orders': validated_orders,
                'sync_time': account.last_sync_at # تاریخ بروزرسانی شده
            }

        except self.connector_service.exceptions.RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded while syncing account {account.label} on {account.exchange.name}: {str(e)}")
            raise RateLimitExceededError(f"Rate limit exceeded on {account.exchange.name}.")
        except self.connector_service.exceptions.AuthenticationError as e:
            logger.error(f"Authentication failed for account {account.label} on {account.exchange.name}: {str(e)}")
            raise InvalidCredentialsError(f"Authentication failed on {account.exchange.name}.")
        except Exception as e:
            logger.error(f"Error syncing account {account.label} on {account.exchange.name}: {str(e)}")
            # ثبت لاگ خطا
            AuditService.log_action(
                user=account.owner,
                action='ACCOUNT_SYNC_ERROR',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={
                    'error': str(e),
                    'account_label': account.label,
                    'exchange': account.exchange.name,
                },
                request=None
            )
            raise ExchangeSyncError(f"Failed to sync account {account.label} from {account.exchange.name}: {str(e)}")

    def _update_balances(self, account: ExchangeAccount, balances_data: list):
        """
        Updates WalletBalance records based on data from the exchange.
        Uses bulk operations for efficiency.
        """
        try:
            # پیدا کردن یا ایجاد کیف پول SPOT
            spot_wallet, created = Wallet.objects.get_or_create(
                exchange_account=account,
                wallet_type='SPOT',
                defaults={'description': f'Spot wallet for {account.exchange.name}'}
            )
            if created:
                logger.info(f"Created default SPOT wallet for account {account.label}.")

            # نرمالایز کردن داده‌ها
            normalized_balances = []
            for balance_item in balances_data:
                 normalized = normalize_data_from_source(balance_item, account.exchange.name, 'BALANCE')
                 if normalized:
                     normalized_balances.append(normalized)

            # گردآوری موجودی‌های جدید/بروز شده
            balance_instances_to_update = []
            balance_keys_to_delete = set() # برای حذف موجودی‌های قدیمی که دیگر وجود ندارند

            for norm_balance in normalized_balances:
                asset_symbol = norm_balance.get('asset')
                if not asset_symbol:
                    continue # نادیده گرفتن اگر نماد نامشخص است

                balance_obj, created = WalletBalance.objects.get_or_create(
                    wallet=spot_wallet,
                    asset_symbol__iexact=asset_symbol,
                    defaults={
                        'asset_symbol': asset_symbol.upper(),
                        'total_balance': norm_balance.get('total', Decimal('0')),
                        'available_balance': norm_balance.get('available', Decimal('0')),
                        'in_order_balance': norm_balance.get('in_order', Decimal('0')),
                        'frozen_balance': norm_balance.get('frozen', Decimal('0')),
                        'borrowed_balance': norm_balance.get('borrowed', Decimal('0')),
                    }
                )
                if not created:
                    # اگر وجود داشت، فقط بروزرسانی کن
                    balance_obj.total_balance = norm_balance.get('total', balance_obj.total_balance)
                    balance_obj.available_balance = norm_balance.get('available', balance_obj.available_balance)
                    balance_obj.in_order_balance = norm_balance.get('in_order', balance_obj.in_order_balance)
                    balance_obj.frozen_balance = norm_balance.get('frozen', balance_obj.frozen_balance)
                    balance_obj.borrowed_balance = norm_balance.get('borrowed', balance_obj.borrowed_balance)
                    balance_instances_to_update.append(balance_obj)

                balance_keys_to_delete.add(asset_symbol.upper())

            # بروزرسانی گروهی موجودی‌های یافت شده
            if balance_instances_to_update:
                WalletBalance.objects.bulk_update(
                    balance_instances_to_update,
                    fields=['total_balance', 'available_balance', 'in_order_balance', 'frozen_balance', 'borrowed_balance', 'updated_at'],
                    batch_size=1000
                )
                logger.info(f"Bulk updated {len(balance_instances_to_update)} balance records for account {account.label}.")

            # حذف موجودی‌هایی که در API وجود نداشتند (اگر نیاز باشد)
            # WalletBalance.objects.filter(wallet=spot_wallet).exclude(asset_symbol__in=balance_keys_to_delete).delete()

        except Exception as e:
            logger.error(f"Error updating balances for account {account.label}: {str(e)}")
            raise DataIntegrityException(f"Failed to update balances for account {account.label}: {str(e)}")

    def _update_order_history(self, account: ExchangeAccount, orders_data: list):
        """
        Updates or creates OrderHistory records based on data from the exchange.
        Uses bulk operations for efficiency.
        """
        try:
            # نرمالایز و اعتبارسنجی داده سفارشات
            normalized_orders = []
            for order_item in orders_data:
                 normalized = normalize_data_from_source(order_item, account.exchange.name, 'ORDER_HISTORY')
                 if normalized:
                     # اطمینان از اینکه فیلدها وجود دارند
                     if not normalized.get('order_id') or not normalized.get('symbol'):
                         logger.warning(f"Skipping order due to missing order_id or symbol: {order_item}")
                         continue
                     validated_order = validate_ohlcv_data(normalized, 'ORDER_HISTORY') # یا تابع اعتبارسنجی سفارش
                     if validated_order:
                         normalized_orders.append(validated_order)

            # گردآوری نمونه‌های سفارش برای ایجاد/بروزرسانی
            order_instances_to_create = []
            order_instances_to_update = []

            for norm_order in normalized_orders:
                # فرض بر این است که نرمالایز کردن، فیلدهای مدل را فراهم می‌کند
                order_defaults = {
                    'symbol': norm_order.get('symbol'),
                    'side': norm_order.get('side'),
                    'order_type': norm_order.get('order_type'),
                    'status': norm_order.get('status'),
                    'price': norm_order.get('price'),
                    'quantity': norm_order.get('quantity'),
                    'executed_quantity': norm_order.get('executed_quantity', Decimal('0')),
                    'cumulative_quote_qty': norm_order.get('cumulative_quote_qty', Decimal('0')),
                    'time_placed': norm_order.get('time_placed'),
                    'time_updated': norm_order.get('time_updated'),
                    'commission': norm_order.get('commission', Decimal('0')),
                    'commission_asset': norm_order.get('commission_asset', ''),
                    # trading_bot: ممکن است نیاز به تعیین دستی یا از طریق منطقی دیگر باشد
                    # 'trading_bot': ... # معمولاً از طریق بات ایجاد می‌شود، نه از API
                }
                order_obj, created = OrderHistory.objects.update_or_create(
                    exchange_account=account,
                    order_id=norm_order.get('order_id'),
                    defaults=order_defaults
                )
                if created:
                    order_instances_to_create.append(order_obj)
                else:
                    order_instances_to_update.append(order_obj)

            # ایجاد گروهی سفارشات جدید
            if order_instances_to_create:
                OrderHistory.objects.bulk_create(order_instances_to_create, batch_size=1000)
                logger.info(f"Bulk created {len(order_instances_to_create)} new order history records for account {account.label}.")

            # بروزرسانی گروهی سفارشات موجود
            if order_instances_to_update:
                OrderHistory.objects.bulk_update(
                    order_instances_to_update,
                    fields=['status', 'executed_quantity', 'time_updated', 'commission', 'updated_at'], # فقط فیلدهایی که ممکن است تغییر کرده باشند
                    batch_size=1000
                )
                logger.info(f"Bulk updated {len(order_instances_to_update)} order history records for account {account.label}.")

        except Exception as e:
            logger.error(f"Error updating order history for account {account.label}: {str(e)}")
            raise DataIntegrityException(f"Failed to update order history for account {account.label}: {str(e)}")

    def place_order(self, account: ExchangeAccount, bot: TradingBot, order_params: dict) -> dict:
        """
        Places an order on the exchange using the account's credentials and bot context.
        """
        try:
            # اعتبارسنجی اولیه داده‌های سفارش (مثلاً وجود فیلدهای اساسی)
            required_params = ['symbol', 'side', 'type', 'amount']
            for param in required_params:
                if param not in order_params:
                    raise OrderExecutionError(f"Missing required order parameter: {param}")

            # چک کردن موجودی (اختیاری، بسته به نوع سفارش و سیاست ریسک)
            # self._check_balance_for_order(account, order_params)

            # ارسال درخواست به صرافی از طریق کانکتور
            response = self.connector_service.place_order(account, order_params)

            # اعتبارسنجی پاسخ
            validated_response = validate_exchange_response(response, 'order_response')

            # نرمالایز کردن پاسخ برای ذخیره در OrderHistory
            normalized_order_data = normalize_data_from_source(validated_response, account.exchange.name, 'ORDER_HISTORY')

            # ایجاد رکورد تاریخچه سفارش (احتمالاً با status 'NEW' یا 'PENDING')
            # توجه: این فقط در صورت موفقیت API است، ممکن است بعداً وضعیت تغییر کند
            order_id = normalized_order_data.get('order_id')
            symbol = normalized_order_data.get('symbol')
            side = normalized_order_data.get('side', '').upper()
            order_type = normalized_order_data.get('order_type', '').upper()
            status = normalized_order_data.get('status', '').upper() # ممکن است 'NEW' باشد
            price = normalized_order_data.get('price', Decimal('0'))
            quantity = normalized_order_data.get('quantity', Decimal('0'))
            executed_qty = normalized_order_data.get('executed_quantity', Decimal('0'))
            cum_quote_qty = normalized_order_data.get('cumulative_quote_qty', Decimal('0'))
            time_placed = normalized_order_data.get('time_placed', timezone.now())
            time_updated = normalized_order_data.get('time_updated', time_placed)
            commission = normalized_order_data.get('commission', Decimal('0'))
            commission_asset = normalized_order_data.get('commission_asset', '')

            # پیدا کردن یا ایجاد کیف پول مرتبط (مثلاً SPOT)
            wallet, created = Wallet.objects.get_or_create(
                exchange_account=account,
                wallet_type='SPOT', # یا نگاشت صحیح
                defaults={'description': f'Spot wallet for {account.exchange.name}'}
            )

            OrderHistory.objects.create(
                exchange_account=account,
                order_id=order_id,
                symbol=symbol,
                side=side,
                order_type=order_type,
                status=status,
                price=price,
                quantity=quantity,
                executed_quantity=executed_qty,
                cumulative_quote_qty=cum_quote_qty,
                time_placed=time_placed,
                time_updated=time_updated,
                commission=commission,
                commission_asset=commission_asset,
                trading_bot=bot, # اتصال به بات
            )

            logger.info(f"Order {order_id} placed successfully by bot {bot.name} on {account.label}")
            # ثبت لاگ حسابرسی
            AuditService.log_action(
                user=account.owner,
                action='ORDER_PLACED',
                target_model_name='OrderHistory',
                target_id=order_id,
                details={
                    'bot_name': bot.name,
                    'account_label': account.label,
                    'exchange': account.exchange.name,
                    'order_details': order_params,
                    'response_status': status,
                },
                request=None
            )
            return validated_response

        except self.connector_service.exceptions.InsufficientBalance as e:
            logger.error(f"Insufficient balance placing order for bot {bot.name} on {account.label}: {str(e)}")
            raise InsufficientBalanceError(f"Insufficient balance on account {account.label}.")
        except self.connector_service.exceptions.RateLimitExceeded as e:
            logger.error(f"Rate limit exceeded placing order for bot {bot.name} on {account.label}: {str(e)}")
            raise RateLimitExceededError(f"Rate limit exceeded on {account.exchange.name}.")
        except self.connector_service.exceptions.AuthenticationError as e:
            logger.error(f"Authentication failed placing order for bot {bot.name} on {account.label}: {str(e)}")
            raise InvalidCredentialsError(f"Authentication failed on {account.exchange.name}.")
        except Exception as e:
            logger.error(f"Error placing order for bot {bot.name} on {account.label}: {str(e)}")
            AuditService.log_action(
                user=account.owner,
                action='ORDER_PLACEMENT_ERROR',
                target_model_name='ExchangeAccount',
                target_id=account.id,
                details={
                    'bot_name': bot.name,
                    'error': str(e),
                    'order_details': order_params,
                },
                request=None
            )
            raise OrderExecutionError(f"Failed to place order: {str(e)}")

    def get_account_balance_for_asset(self, account: ExchangeAccount, asset_symbol: str) -> Decimal:
        """
        Retrieves the available balance for a specific asset in the account's Spot wallet.
        """
        try:
            wallet = Wallet.objects.get(exchange_account=account, wallet_type='SPOT')
            balance_record = WalletBalance.objects.get(wallet=wallet, asset_symbol__iexact=asset_symbol)
            return balance_record.available_balance
        except (Wallet.DoesNotExist, WalletBalance.DoesNotExist):
            logger.warning(f"Balance for asset {asset_symbol} not found in Spot wallet for account {account.label}")
            return Decimal('0')

    def cancel_order(self, account: ExchangeAccount, order_id: str) -> dict:
        """
        Cancels an existing order on the exchange.
        """
        try:
            response = self.connector_service.cancel_order(account, order_id)
            validated_response = validate_exchange_response(response, 'cancel_response')

            # به‌روزرسانی وضعیت سفارش در پایگاه داده (اختیاری، ممکن است sync بعدی انجام دهد)
            try:
                order_history = OrderHistory.objects.get(exchange_account=account, order_id=order_id)
                order_history.status = 'CANCELED'
                order_history.time_updated = timezone.now()
                order_history.save(update_fields=['status', 'time_updated'])
            except OrderHistory.DoesNotExist:
                logger.warning(f"Order history record for {order_id} not found for cancellation update.")

            logger.info(f"Order {order_id} cancelled successfully on {account.label}")
            AuditService.log_action(
                user=account.owner,
                action='ORDER_CANCELED',
                target_model_name='OrderHistory',
                target_id=order_id,
                details={'account_label': account.label, 'exchange': account.exchange.name},
                request=None
            )
            return validated_response
        except self.connector_service.exceptions.OrderNotFound as e:
            logger.error(f"Order {order_id} not found on exchange for cancellation on {account.label}: {str(e)}")
            raise OrderExecutionError(f"Order {order_id} not found on exchange.")
        except Exception as e:
            logger.error(f"Error cancelling order {order_id} on {account.label}: {str(e)}")
            AuditService.log_action(
                user=account.owner,
                action='ORDER_CANCELLATION_ERROR',
                target_model_name='OrderHistory',
                target_id=order_id,
                details={'error': str(e)},
                request=None
            )
            raise OrderExecutionError(f"Failed to cancel order {order_id}: {str(e)}")

    def _check_balance_for_order(self, account: ExchangeAccount, order_params: dict):
        """
        Checks if the account has sufficient balance for the order.
        This is a simplified example and might require more complex logic based on order type and asset.
        """
        asset_to_check = order_params['symbol'] # ساده‌سازی: فرض می‌کنیم نماد معادل ارز مبدا/مقصد است
        side = order_params['side'].upper()
        amount = Decimal(str(order_params['amount']))
        price = Decimal(str(order_params.get('price', 0))) # برای limit order

        current_balance = self.get_account_balance_for_asset(account, asset_to_check)

        required_balance = amount if side == 'SELL' else (amount * price) # محاسبه ساده

        if current_balance < required_balance:
            raise InsufficientBalanceError(f"Insufficient balance for {side} order of {amount} {asset_to_check}. Required: {required_balance}, Available: {current_balance}")


# --- سایر سرویس‌های مرتبط با اپلیکیشن exchanges ---
# می‌توانید سرویس‌های دیگری مانند ExchangeConnectionService، InstrumentDetailsService، یا MarketDataSyncService تعریف کنید

class ExchangeConnectionService:
    """
    Service for managing exchange connections (creation, validation, health check).
    """
    def __init__(self):
        self.connector_service = ConnectorService()

    def validate_connection(self, account: ExchangeAccount) -> bool:
        """
        Validates the connection to the exchange using stored credentials.
        """
        try:
            conn = self.connector_service.test_connection(
                api_key=account.api_key, # از property رمزنگاری شده استفاده می‌کند
                api_secret=account.api_secret, # از property رمزنگاری شده استفاده می‌کند
                exchange_name=account.exchange.name,
                extra_creds=account.extra_credentials
            )
            return conn.is_valid()
        except Exception as e:
            logger.error(f"Connection validation failed for account {account.label} on {account.exchange.name}: {str(e)}")
            return False

    def get_connection_status(self, account: ExchangeAccount) -> dict:
        """
        Gets the current connection status from the connector.
        """
        try:
            return self.connector_service.get_connection_status(account)
        except Exception as e:
            logger.error(f"Error getting connection status for account {account.label}: {str(e)}")
            return {'status': 'error', 'message': str(e)}

# --- سرویس برای مدیریت داده بازار ---
class ExchangeMarketDataService:
    """
    Service for fetching and managing market data specifically related to exchange accounts.
    """
    def __init__(self):
        self.market_data_service = MarketDataService() # از سرویس مرکزی استفاده می‌کند

    def get_latest_price(self, account: ExchangeAccount, symbol: str) -> Decimal:
        """
        Retrieves the latest price for a symbol from the specific exchange account's source.
        """
        # ممکن است نیاز به دسترسی مستقیم به کانکتور باشد
        try:
            raw_ticker = self.connector_service.get_ticker(account, symbol)
            normalized_data = normalize_data_from_source(raw_ticker, account.exchange.name, 'TICKER')
            return normalized_data.get('last_price', Decimal('0'))
        except Exception as e:
            logger.error(f"Failed to get latest price for {symbol} on {account.label}: {str(e)}")
            raise DataFetchError(f"Could not fetch price for {symbol} from {account.exchange.name}.")

    def get_historical_candles(self, account: ExchangeAccount, symbol: str, interval: str, limit: int = 100) -> list:
        """
        Retrieves historical OHLCV data for a symbol from the specific exchange account.
        """
        try:
            exchange_symbol = self._get_exchange_symbol(account, symbol) # ممکن است نیاز به نگاشت نماد باشد
            raw_candles = self.connector_service.get_ohlcv(account, exchange_symbol, interval, limit)
            normalized_candles = []
            for raw_candle in raw_candles:
                 norm = normalize_data_from_source(raw_candle, account.exchange.name, 'OHLCV')
                 if norm:
                     validated_candle = validate_ohlcv_data(norm, 'OHLCV') # یا تابع اعتبارسنجی داده OHLCV
                     if validated_candle:
                         normalized_candles.append(validated_candle)
            return normalized_candles
        except Exception as e:
            logger.error(f"Failed to get historical candles for {symbol} on {account.label}: {str(e)}")
            raise DataFetchError(f"Could not fetch candles for {symbol} from {account.exchange.name}.")

    def _get_exchange_symbol(self, account: ExchangeAccount, internal_symbol: str) -> str:
        """
        Maps an internal symbol to the exchange-specific symbol for this account.
        This requires an InstrumentExchangeMap model or similar.
        """
        try:
            from apps.instruments.models import InstrumentExchangeMap
            mapping = InstrumentExchangeMap.objects.get(
                instrument__symbol__iexact=internal_symbol,
                exchange_account__exchange=account.exchange # از exchange_account صرافی استفاده می‌کنیم
            )
            return mapping.exchange_symbol
        except InstrumentExchangeMap.DoesNotExist:
            logger.warning(f"No exchange symbol mapping found for {internal_symbol} on {account.exchange.name}. Using internal symbol.")
            return internal_symbol


# --- سرویس برای مدیریت ارتباط با عامل (Agent) ---
class ExchangeAgentService:
    """
    Service for managing interactions between exchange accounts and trading agents.
    """
    def notify_agent_of_order_update(self, agent_id: str, order_data: dict):
        """
        Sends an order update notification to a specific agent.
        This might involve sending a message via the MessageBus or Celery task.
        """
        try:
            from apps.core.messaging import MessageBus # import داخل تابع
            message_bus = MessageBus()
            message = {
                'type': 'ORDER_UPDATE',
                'data': order_data,
                'timestamp': timezone.now().isoformat()
            }
            message_bus.publish(f'agent.{agent_id}', message)
            logger.info(f"Order update notification sent to agent {agent_id}.")
        except Exception as e:
            logger.error(f"Failed to notify agent {agent_id} of order update: {str(e)}")
            # ممکن است بخواهید یک تاسک Celery برای ارسال پیام ایجاد کنید
            # from apps.core.tasks import send_agent_notification_task
            # send_agent_notification_task.delay(agent_id, 'ORDER_UPDATE', order_data)

    def notify_agents_of_market_data(self, symbol: str, exchange_name: str, data: dict):
        """
        Broadcasts market data to interested agents.
        """
        try:
            from apps.core.messaging import MessageBus
            message_bus = MessageBus()
            message = {
                'type': 'MARKET_DATA_UPDATE',
                'symbol': symbol,
                'exchange': exchange_name,
                'data': data,
                'timestamp': timezone.now().isoformat()
            }
            # ارسال به یک چنل عمومی یا چنل‌های مرتبط با نماد
            message_bus.broadcast(message, exclude_senders=[]) # ممکن است نیاز به فیلتر کردن داشته باشد
            logger.debug(f"Market data broadcast sent for {symbol} on {exchange_name}.")
        except Exception as e:
            logger.error(f"Failed to broadcast market data for {symbol} on {exchange_name}: {str(e)}")


logger.info("Exchanges services loaded successfully.")
