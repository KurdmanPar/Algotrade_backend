# apps/connectors/nobitex_connector.py
import requests
import time
from datetime import datetime
from .base import ExchangeConnector
from .registry import register_connector
import logging

logger = logging.getLogger(__name__)

@register_connector('NOBITEX') # ثبت کانکتور با کد صرافی
class NobitexConnector(ExchangeConnector):
    """
    پیاده‌سازی کامل اتصال‌دهنده برای صرافی نوبیتکس.
    این کانکتور با استفاده از JWT Token برای احراز هویت کار می‌کند.
    """
    def __init__(self, api_key: str, api_secret: str, exchange_account_id: int, **kwargs):
        super().__init__(api_key, api_secret, exchange_account_id, **kwargs)
        # api_key در نوبیتکس معمولاً یک token است، نه یک کلید
        # api_secret ممکن است یک کلید باشد یا خالی (بسته به نحوه تولید token)
        self.jwt_token = api_key  # api_key در اینجا token است
        self.api_base_url = self.exchange_account.exchange.connector_config.api_base_url
        if self.exchange_account.exchange.connector_config.is_sandbox_mode_default:
            self.api_base_url = self.exchange_account.exchange.connector_config.sandbox_api_base_url
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.jwt_token}'
        })

    def connect(self) -> bool:
        try:
            # تست اتصال با یک درخواست ساده (مثلاً دریافت پروفایل)
            url = f"{self.api_base_url}/users/profile"
            response = self.session.get(url)
            if response.status_code == 200:
                logger.info("Successfully connected to Nobitex.")
                return True
            else:
                logger.error(f"Failed to connect to Nobitex: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Exception during Nobitex connection: {e}")
            return False

    def disconnect(self):
        self.session = None

    def is_connected(self) -> bool:
        return self.session is not None

    def get_balance(self, currency: str = None) -> dict:
        try:
            self._handle_rate_limit('/users/wallets/list')
            url = f"{self.api_base_url}/users/wallets/list"
            payload = {'currency': currency} if currency else {}
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('get_balance', '/users/wallets/list', payload, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('get_balance', '/users/wallets/list', {'currency': currency}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, **kwargs):
        try:
            self._handle_rate_limit('/market/orders/add')
            url = f"{self.api_base_url}/market/orders/add"
            # تبدیل side و type به فرمت مورد نیاز نوبیتکس
            side_nobitex = 'buy' if side.upper() == 'BUY' else 'sell'
            type_nobitex = 'limit' if order_type.upper() == 'LIMIT' else 'market'
            payload = {
                'symbol': symbol.lower(), # نوبیتکس نماد را با حروف کوچک می‌خواهد
                'side': side_nobitex,
                'type': type_nobitex,
                'amount': str(quantity),
            }
            if price:
                payload['price'] = str(price)
            # اضافه کردن سایر پارامترهای kwargs
            payload.update(kwargs)

            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('place_order', '/market/orders/add', payload, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('place_order', '/market/orders/add', {'symbol': symbol, 'side': side, 'type': order_type, 'amount': quantity, 'price': price}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def cancel_order(self, order_id: str, symbol: str, **kwargs):
        try:
            self._handle_rate_limit('/market/orders/cancel')
            url = f"{self.api_base_url}/market/orders/cancel"
            payload = {'order_id': order_id, 'symbol': symbol.lower()}
            payload.update(kwargs)
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('cancel_order', '/market/orders/cancel', payload, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('cancel_order', '/market/orders/cancel', {'order_id': order_id, 'symbol': symbol}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def get_order_status(self, order_id: str, symbol: str, **kwargs):
        try:
            self._handle_rate_limit('/market/orders/status')
            url = f"{self.api_base_url}/market/orders/status"
            # نوبیتکس وضعیت سفارش را با ارسال order_id در بدنه می‌دهد
            payload = {'order_ids': [order_id]} # نوبیتکس از آرایه order_ids استفاده می‌کند
            payload.update(kwargs)
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            # Nobitex یک آرایه برمی‌گرداند، ما فقط اولین نتیجه را نیاز داریم
            order_status = data.get('orders', [{}])[0] if data.get('orders') else {}
            self._log_interaction('get_order_status', '/market/orders/status', payload, order_status, response.status_code)
            return order_status
        except requests.exceptions.RequestException as e:
            self._log_interaction('get_order_status', '/market/orders/status', {'order_ids': [order_id]}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    # متدهای بیشتر نوبیتکس:

    def get_open_orders(self, symbol: str = None) -> dict:
        try:
            self._handle_rate_limit('/market/orders/list')
            url = f"{self.api_base_url}/market/orders/list"
            payload = {'status': 'pending'} # فقط سفارش‌های باز
            if symbol:
                payload['symbol'] = symbol.lower()
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('get_open_orders', '/market/orders/list', payload, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('get_open_orders', '/market/orders/list', payload, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def get_trades_history(self, symbol: str = None, limit: int = 100) -> dict:
        try:
            self._handle_rate_limit('/market/trades/list')
            url = f"{self.api_base_url}/market/trades/list"
            payload = {'limit': limit}
            if symbol:
                payload['symbol'] = symbol.lower()
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('get_trades_history', '/market/trades/list', payload, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('get_trades_history', '/market/trades/list', payload, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def get_market_depth(self, symbol: str) -> dict:
        try:
            self._handle_rate_limit('/market/depth')
            url = f"{self.api_base_url}/market/depth"
            payload = {'symbol': symbol.lower()}
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('get_market_depth', '/market/depth', payload, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('get_market_depth', '/market/depth', payload, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    def get_server_time(self) -> dict:
        try:
            # این درخواست معمولاً نیاز به احراز هویت ندارد
            url = f"{self.api_base_url}/public/time"
            response = self.session.get(url)
            response.raise_for_status()
            data = response.json()
            self._log_interaction('get_server_time', '/public/time', {}, data, response.status_code)
            return data
        except requests.exceptions.RequestException as e:
            self._log_interaction('get_server_time', '/public/time', {}, {'error': str(e)}, error_message=str(e))
            return {'error': str(e)}

    # سایر متدها...
    # به عنوان مثال: withdraw, deposit, get_deposit_address و غیره
    # باید بر اساس مستندات نوبیتکس پیاده‌سازی شوند.
