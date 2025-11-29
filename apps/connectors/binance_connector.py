# apps/connectors/binance_connector.py
from .base import ExchangeConnector
from .registry import register_connector
from binance.client import Client as BinanceClient
from binance.exceptions import BinanceAPIException
import logging

logger = logging.getLogger(__name__)

@register_connector('BINANCE') # ثبت کانکتور با کد صرافی
class BinanceConnector(ExchangeConnector):
    """
    پیاده‌سازی کامل اتصال‌دهنده برای صرافی بایننس.
    """
    def __init__(self, api_key: str, api_secret: str, exchange_account_id: int, **kwargs):
        super().__init__(api_key, api_secret, exchange_account_id, **kwargs)
        self.client = None

    def connect(self) -> bool:
        try:
            self.client = BinanceClient(api_key=self.api_key, api_secret=self.api_secret)
            account_info = self.client.get_account()
            logger.info("Successfully connected to Binance.")
            return True
        except BinanceAPIException as e:
            logger.error(f"Failed to connect to Binance: {e}")
            return False

    def disconnect(self):
        self.client = None

    def is_connected(self) -> bool:
        return self.client is not None

    def get_balance(self, currency: str = None) -> dict:
        try:
            if currency:
                balance_info = self.client.get_asset_balance(asset=currency)
                return {currency: balance_info['free']}
            else:
                return self.client.get_account()['balances']
        except BinanceAPIException as e:
            self._log_interaction('get_balance', '/api/v3/account', {}, {'error': str(e)}, error_message=str(e))
            return {}

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, **kwargs):
        try:
            # چک کردن محدودیت
            self._handle_rate_limit('/api/v3/order')
            if order_type == 'MARKET':
                result = self.client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity)
            elif order_type == 'LIMIT':
                result = self.client.create_order(symbol=symbol, side=side, type=order_type, quantity=quantity, price=price)
            else:
                raise ValueError(f"Unsupported order type: {order_type}")

            self._log_interaction('place_order', '/api/v3/order', {'symbol': symbol, 'side': side, 'type': order_type, 'quantity': quantity, 'price': price}, result)
            return result
        except BinanceAPIException as e:
            self._log_interaction('place_order', '/api/v3/order', {'symbol': symbol, 'side': side, 'type': order_type, 'quantity': quantity, 'price': price}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def cancel_order(self, order_id: str, symbol: str, **kwargs):
        try:
            self._handle_rate_limit('/api/v3/order')
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            self._log_interaction('cancel_order', '/api/v3/order', {'orderId': order_id, 'symbol': symbol}, result)
            return result
        except BinanceAPIException as e:
            self._log_interaction('cancel_order', '/api/v3/order', {'orderId': order_id, 'symbol': symbol}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def get_order_status(self, order_id: str, symbol: str, **kwargs):
        try:
            self._handle_rate_limit('/api/v3/order')
            result = self.client.get_order(symbol=symbol, orderId=order_id)
            self._log_interaction('get_order_status', '/api/v3/order', {'orderId': order_id, 'symbol': symbol}, result)
            return result
        except BinanceAPIException as e:
            self._log_interaction('get_order_status', '/api/v3/order', {'orderId': order_id, 'symbol': symbol}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    # سایر متدها...