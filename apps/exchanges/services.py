# apps/exchanges/services.py

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.core.exceptions import ValidationError
from .models import (
    ExchangeAccount,
    Wallet,
    WalletBalance,
    OrderHistory,
    MarketDataCandle,
    Exchange
)
from apps.bots.models import TradingBot # فرض بر این است که مدل وجود دارد
from apps.connectors.service import ConnectorService # فرض بر این است که این سرویس اتصال به صرافی وجود دارد
from apps.market_data.service import MarketDataService # فرض بر این است که این سرویس مدیریت داده بازار وجود دارد
from .exceptions import ExchangeSyncError, DataFetchError, OrderExecutionError # فرض بر این است که این استثناها وجود دارند
from .helpers import validate_exchange_response # فرض بر این است که این تابع کمکی وجود دارد

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
        """
        try:
            # 1. دریافت اطلاعات حساب از صرافی
            exchange_info = self.connector_service.get_account_info(account)
            validated_info = validate_exchange_response(exchange_info, 'account_info')
            logger.info(f"Fetched account info for {account.label} on {account.exchange.name}")

            # 2. دریافت موجودی‌ها
            balances_raw = self.connector_service.get_account_balances(account)
            validated_balances = validate_exchange_response(balances_raw, 'balances')
            logger.info(f"Fetched balances for {account.label}")

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
                account.save(update_fields=['account_info', 'trading_permissions'])

                # به‌روزرسانی موجودی‌ها
                self._update_balances(account, validated_balances)

                # به‌روزرسانی یا ایجاد تاریخچه سفارشات
                self._update_order_history(account, validated_orders)

            # 5. بازگرداندن اطلاعات همگام‌سازی شده
            return {
                'account_info': validated_info,
                'balances': validated_balances,
                'orders': validated_orders,
                'sync_time': timezone.now()
            }

        except Exception as e:
            logger.error(f"Error syncing account {account.label}: {str(e)}")
            raise ExchangeSyncError(f"Failed to sync account {account.label} from {account.exchange.name}: {str(e)}")

    def _update_balances(self, account: ExchangeAccount, balances_data: list):
        """
        Updates WalletBalance records based on data from the exchange.
        """
        for balance_item in balances_data:
            asset_symbol = balance_item.get('asset')
            total = Decimal(str(balance_item.get('total', 0)))
            available = Decimal(str(balance_item.get('available', 0)))
            in_order = Decimal(str(balance_item.get('in_order', 0)))
            frozen = Decimal(str(balance_item.get('frozen', 0)))
            borrowed = Decimal(str(balance_item.get('borrowed', 0)))

            # فرض بر این است که یک کیف پول Spot وجود دارد یا باید یک نگاشت ایجاد شود
            # برای سادگی، فرض می‌کنیم کل موجودی مربوط به کیف پول Spot است
            wallet, created = Wallet.objects.get_or_create(
                exchange_account=account,
                wallet_type='SPOT', # یا نگاشت صحیح
                defaults={'description': f'Spot wallet for {account.exchange.name}'}
            )

            wallet_balance, created = WalletBalance.objects.update_or_create(
                wallet=wallet,
                asset_symbol=asset_symbol,
                defaults={
                    'total_balance': total,
                    'available_balance': available,
                    'in_order_balance': in_order,
                    'frozen_balance': frozen,
                    'borrowed_balance': borrowed,
                }
            )
            if created:
                logger.info(f"Created new balance record for {asset_symbol} in wallet {wallet.id}")
            else:
                logger.info(f"Updated balance record for {asset_symbol} in wallet {wallet.id}")

    def _update_order_history(self, account: ExchangeAccount, orders_data: list):
        """
        Updates or creates OrderHistory records based on data from the exchange.
        """
        for order_item in orders_data:
            order_id = order_item.get('id')
            # فرض بر این است که کلیدهای مربوطه در order_item وجود دارند
            # نیاز به نگاشت کلیدها بسته به ساختار API صرافی دارد
            # مثال ساختار کلی:
            symbol = order_item.get('symbol')
            side = order_item.get('side', '').upper()
            order_type = order_item.get('type', '').upper()
            status = order_item.get('status', '').upper()
            price = Decimal(str(order_item.get('price', 0)))
            quantity = Decimal(str(order_item.get('amount', 0))) # یا 'quantity'
            executed_qty = Decimal(str(order_item.get('filled', 0)))
            cum_quote_qty = Decimal(str(order_item.get('cost', 0))) # یا 'cumulative_cost'
            time_placed_str = order_item.get('timestamp') # یا 'datetime' - بسته به API
            time_updated_str = order_item.get('lastTradeTimestamp') # یا 'updated_at' - بسته به API
            commission = Decimal(str(order_item.get('fee', {}).get('cost', 0)))
            commission_asset = order_item.get('fee', {}).get('currency', '')

            # تبدیل زمان‌ها (بسته به فرمت API)
            try:
                time_placed = timezone.make_aware(datetime.fromtimestamp(time_placed_str / 1000)) if time_placed_str else timezone.now()
                time_updated = timezone.make_aware(datetime.fromtimestamp(time_updated_str / 1000)) if time_updated_str else time_placed
            except (ValueError, TypeError):
                time_placed = timezone.now()
                time_updated = time_placed
                logger.warning(f"Could not parse timestamp for order {order_id} on {account.label}, using current time.")

            # پیدا کردن یا ایجاد کیف پول مرتبط (مثلاً SPOT)
            wallet, created = Wallet.objects.get_or_create(
                exchange_account=account,
                wallet_type='SPOT', # یا نگاشت صحیح
                defaults={'description': f'Spot wallet for {account.exchange.name}'}
            )

            # فرض بر این است که سفارش مربوط به همین کیف پول است
            order_history, created = OrderHistory.objects.update_or_create(
                exchange_account=account,
                order_id=order_id,
                defaults={
                    'symbol': symbol,
                    'side': side,
                    'order_type': order_type,
                    'status': status,
                    'price': price,
                    'quantity': quantity,
                    'executed_quantity': executed_qty,
                    'cumulative_quote_qty': cum_quote_qty,
                    'time_placed': time_placed,
                    'time_updated': time_updated,
                    'commission': commission,
                    'commission_asset': commission_asset,
                    # trading_bot: ممکن است نیاز به تعیین دستی یا از طریق منطقی دیگر باشد
                }
            )
            if created:
                logger.info(f"Created new order history record for {order_id} on {account.label}")
            else:
                logger.info(f"Updated order history record for {order_id} on {account.label}")

    def place_order(self, account: ExchangeAccount, bot: TradingBot, order_params: dict) -> dict:
        """
        Places an order on the exchange using the account's credentials and bot context.
        """
        try:
            # اعتبارسنجی order_params ممکن است لازم باشد
            # مثلاً بررسی وجود symbol، side، type، amount/quantity، price (برای limit)
            # و همچنین بررسی محدودیت‌ها در account_info

            # ارسال درخواست به صرافی از طریق کانکتور
            response = self.connector_service.place_order(account, order_params)

            # اعتبارسنجی پاسخ
            validated_response = validate_exchange_response(response, 'order_response')

            # ایجاد رکورد تاریخچه سفارش (احتمالاً با status 'NEW' یا 'PENDING')
            # توجه: این فقط در صورت موفقیت API است، ممکن است بعداً وضعیت تغییر کند
            order_id = validated_response.get('id')
            symbol = validated_response.get('symbol')
            side = validated_response.get('side', '').upper()
            order_type = validated_response.get('type', '').upper()
            status = validated_response.get('status', '').upper() # ممکن است 'NEW' باشد
            price = Decimal(str(validated_response.get('price', 0)))
            quantity = Decimal(str(validated_response.get('amount', 0)))
            executed_qty = Decimal(str(validated_response.get('filled', 0)))
            cum_quote_qty = Decimal(str(validated_response.get('cost', 0)))
            time_placed_str = validated_response.get('timestamp') # یا 'datetime'
            time_updated_str = validated_response.get('lastTradeTimestamp') # یا 'updated_at'

            try:
                time_placed = timezone.make_aware(datetime.fromtimestamp(time_placed_str / 1000)) if time_placed_str else timezone.now()
                time_updated = timezone.make_aware(datetime.fromtimestamp(time_updated_str / 1000)) if time_updated_str else time_placed
            except (ValueError, TypeError):
                time_placed = timezone.now()
                time_updated = time_placed
                logger.warning(f"Could not parse timestamp for new order {order_id}, using current time.")

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
                trading_bot=bot, # اتصال به بات
                # commission و commission_asset ممکن است بعداً از صرافی گرفته شود
            )

            logger.info(f"Order {order_id} placed successfully by bot {bot.name} on {account.label}")
            return validated_response

        except Exception as e:
            logger.error(f"Error placing order for bot {bot.name} on {account.label}: {str(e)}")
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
            return validated_response
        except Exception as e:
            logger.error(f"Error cancelling order {order_id} on {account.label}: {str(e)}")
            raise OrderExecutionError(f"Failed to cancel order {order_id}: {str(e)}")

# سایر سرویس‌های مرتبط می‌توانند در این فایل یا فایل‌های جداگانه تعریف شوند
# مثلاً یک سرویس برای مدیریت اتصالات یا یک سرویس برای مدیریت داده‌های تاریخی
