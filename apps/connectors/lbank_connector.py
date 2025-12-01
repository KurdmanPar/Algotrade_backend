# # apps/connectors/lbank_connector.py
# import requests
# import hashlib
# import hmac
# import time
# from urllib.parse import urlencode
# from .base import ExchangeConnector
# from .registry import register_connector
# import logging
#
# logger = logging.getLogger(__name__)
#
# @register_connector('LBANK') # ثبت کانکتور با کد صرافی
# class LBankConnector(ExchangeConnector):
#     """
#     پیاده‌سازی کامل اتصال‌دهنده برای صرافی LBank.
#     """
#     def __init__(self, api_key: str, api_secret: str, exchange_account_id: int, **kwargs):
#         super().__init__(api_key, api_secret, exchange_account_id, **kwargs)
#         self.api_base_url = self.exchange_account.exchange.connector_config.api_base_url
#         if self.exchange_account.exchange.connector_config.is_sandbox_mode_default:
#             self.api_base_url = self.exchange_account.exchange.connector_config.sandbox_api_base_url
#         self.session = requests.Session()
#         self.session.headers.update({
#             'Content-Type': 'application/x-www-form-urlencoded',
#         })
#
#     def _sign_request(self, params: dict, timestamp: str) -> str:
#         """
#         امضای درخواست بر اساس مستندات LBank.
#         """
#         params['api_key'] = self.api_key
#         params['timestamp'] = timestamp
#         # مرتب‌سازی پارامترها برای ایجاد پیام
#         query_string = urlencode(sorted(params.items()))
#         signature = hmac.new(
#             self.api_secret.encode('utf-8'),
#             query_string.encode('utf-8'),
#             hashlib.sha256
#         ).hexdigest().upper()
#         return signature
#
#     def connect(self) -> bool:
#         try:
#             # تست اتصال با یک درخواست ساده (مثلاً دریافت وضعیت سرور)
#             timestamp = str(int(time.time() * 1000))
#             params = {'action': 'server_time', 'timestamp': timestamp}
#             params['sign'] = self._sign_request({}, timestamp)
#             url = f"{self.api_base_url}/v2/server_time.do"
#             response = self.session.post(url, data=params)
#             if response.status_code == 200:
#                 logger.info("Successfully connected to LBank.")
#                 return True
#             else:
#                 logger.error(f"Failed to connect to LBank: {response.status_code} - {response.text}")
#                 return False
#         except Exception as e:
#             logger.error(f"Exception during LBank connection: {e}")
#             return False
#
#     def disconnect(self):
#         self.session = None
#
#     def is_connected(self) -> bool:
#         return self.session is not None
#
#     def get_balance(self, currency: str = None) -> dict:
#         try:
#             self._handle_rate_limit('/v2/user_info.do')
#             timestamp = str(int(time.time() * 1000))
#             params = {'action': 'user_info', 'timestamp': timestamp}
#             params['sign'] = self._sign_request({}, timestamp)
#             url = f"{self.api_base_url}/v2/user_info.do"
#             response = self.session.post(url, data=params)
#             response.raise_for_status()
#             data = response.json()
#             self._log_interaction('get_balance', '/v2/user_info.do', params, data, response.status_code)
#             return data
#         except requests.exceptions.RequestException as e:
#             self._log_interaction('get_balance', '/v2/user_info.do', {}, {'error': str(e)}, error_message=str(e))
#             return {'error': str(e)}
#
#     def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, **kwargs):
#         try:
#             self._handle_rate_limit('/v2/create_order.do')
#             timestamp = str(int(time.time() * 1000))
#             params = {
#                 'action': 'create_order',
#                 'symbol': symbol.lower(), # LBank معمولاً نماد را با حروف کوچک می‌خواهد
#                 'type': side.lower(), # buy/sell
#                 'amount': str(quantity),
#                 'timestamp': timestamp
#             }
#             if price:
#                 params['price'] = str(price)
#             # تبدیل نوع سفارش (مثلاً limit -> buy/sell)
#             # اینجا فقط یک نگاشت ساده تعریف می‌کنیم
#             if order_type.lower() in ['limit', 'market']:
#                 # LBank نوع سفارش را از طریق 'type' مشخص می‌کند
#                 # 'type': 'buy' یا 'sell' برای مارکت، یا 'buy_maker'/'sell_maker' برای لیمیت
#                 if order_type.lower() == 'limit':
#                     params['type'] = params['type'] + '_maker'
#             params.update(kwargs)
#             params['sign'] = self._sign_request(params, timestamp)
#             url = f"{self.api_base_url}/v2/create_order.do"
#             response = self.session.post(url, data=params)
#             response.raise_for_status()
#             data = response.json()
#             self._log_interaction('place_order', '/v2/create_order.do', params, data, response.status_code)
#             return data
#         except requests.exceptions.RequestException as e:
#             self._log_interaction('place_order', '/v2/create_order.do', {'symbol': symbol, 'side': side, 'type': order_type, 'quantity': quantity, 'price': price}, {'error': str(e)}, error_message=str(e))
#             return {'error': str(e)}
#
#     def cancel_order(self, order_id: str, symbol: str, **kwargs):
#         try:
#             self._handle_rate_limit('/v2/cancel_order.do')
#             timestamp = str(int(time.time() * 1000))
#             params = {
#                 'action': 'cancel_order',
#                 'symbol': symbol.lower(),
#                 'order_id': order_id,
#                 'timestamp': timestamp
#             }
#             params.update(kwargs)
#             params['sign'] = self._sign_request(params, timestamp)
#             url = f"{self.api_base_url}/v2/cancel_order.do"
#             response = self.session.post(url, data=params)
#             response.raise_for_status()
#             data = response.json()
#             self._log_interaction('cancel_order', '/v2/cancel_order.do', params, data, response.status_code)
#             return data
#         except requests.exceptions.RequestException as e:
#             self._log_interaction('cancel_order', '/v2/cancel_order.do', {'order_id': order_id, 'symbol': symbol}, {'error': str(e)}, error_message=str(e))
#             return {'error': str(e)}
#
#     def get_order_status(self, order_id: str, symbol: str, **kwargs):
#         # LBank ممکن است API مستقیم برای گرفتن وضعیت یک سفارش نداشته باشد.
#         # ممکن است لازم باشد از `get_open_orders` یا `get_orders_info` استفاده کرد.
#         # در اینجا یک پیاده‌سازی موقت با `get_orders_info` ارائه می‌شود.
#         try:
#             self._handle_rate_limit('/v2/get_orders_info.do')
#             timestamp = str(int(time.time() * 1000))
#             params = {
#                 'action': 'get_orders_info',
#                 'symbol': symbol.lower(),
#                 'order_id': order_id,
#                 'timestamp': timestamp
#             }
#             params.update(kwargs)
#             params['sign'] = self._sign_request(params, timestamp)
#             url = f"{self.api_base_url}/v2/get_orders_info.do"
#             response = self.session.post(url, data=params)
#             response.raise_for_status()
#             data = response.json()
#             self._log_interaction('get_order_status', '/v2/get_orders_info.do', params, data, response.status_code)
#             return data
#         except requests.exceptions.RequestException as e:
#             self._log_interaction('get_order_status', '/v2/get_orders_info.do', {'order_id': order_id, 'symbol': symbol}, {'error': str(e)}, error_message=str(e))
#             return {'error': str(e)}
#
#     # سایر متدها...
#     # به عنوان مثال: get_open_orders, get_trade_history و غیره
#     # باید بر اساس مستندات LBank پیاده‌سازی شوند.

######################################

# apps/connectors/lbank_connector.py
from .connector_interface import IExchangeConnector
import aiohttp
import asyncio
import hashlib
import hmac
import time
from urllib.parse import urlencode
import json


class LBankConnector(IExchangeConnector):
    def __init__(self, config, credential, agent):
        self.config = config
        self.credential = credential
        self.agent = agent
        self.ws_url = config.data_source.ws_url
        self.api_key = credential.api_key_encrypted  # فرض می‌کنیم که از مدل APICredential بگیرد
        self.api_secret = credential.api_secret_encrypted
        self.session = aiohttp.ClientSession()
        self.is_connected = False

    async def connect(self):
        # اتصال به WebSocket LBank
        # مثال: wss://www.lbkex.net/ws/V2/
        # ارسال پیام اشتراک (subscribe) بر اساس کانفیگ
        pass

    async def disconnect(self):
        if self.session:
            await self.session.close()
        self.is_connected = False

    def _sign_message(self, params: dict) -> str:
        # پیاده‌سازی الگوریتم امضای LBank
        # معمولاً شامل مرتب‌سازی پارامترها، افزودن secret، hash با SHA256 و ...
        query_string = urlencode(sorted(params.items()))
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest().upper()
        return signature

    async def listen(self):
        # حلقه اصلی دریافت پیام از WebSocket
        # مثال:
        # async with websockets.connect(self.ws_url) as websocket:
        #     while self.is_connected:
        #         message = await websocket.recv()
        #         yield json.loads(message)
        pass

    def get_historical_data(self, symbol: str, timeframe: str, start: str, end: str):
        # فراخوانی API تاریخی LBank
        # مثال: /v2/kline.do?symbol=btc_usdt&size=100&time=1min
        pass

    def subscribe(self, symbol: str, data_type: str):
        # ارسال پیام اشتراک به WebSocket
        # مثلاً برای تیک: {"action": "subscribe", "pair": "btc_usdt", "type": "tick"}
        pass

    def unsubscribe(self, symbol: str, data_type: str):
        # ارسال پیام لغو اشتراک
        pass