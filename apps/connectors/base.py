# apps/connectors/base.py
from abc import ABC, abstractmethod

class ExchangeConnector(ABC):
    """
    کلاس پایه انتزاعی (Abstract Base Class) که نقشه راه (Interface)
    را برای تمام اتصال‌دهنده‌های صرافی تعریف می‌کند.
    هر اتصال‌دهنده صرافی (مثل Binance, Coinbase) باید این قرارداد را پیاده‌سازی کند.
    """
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        سازنده کلاس برای ذخیره کلیدهای API.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = kwargs.get('passphrase')  # برای صرافی‌هایی مثل OKX

    @abstractmethod
    def connect(self) -> bool:
        """
        اتصال به صرافی و تایید اعتبارنامه‌ها.
        """
        pass

    @abstractmethod
    def get_balance(self, currency: str = None) -> dict:
        """
        دریافت موجودی کل حساب یا یک ارز خاص.
        """
        pass

    @abstractmethod
    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, **kwargs) -> dict:
        """
        ثبت یک سفارش جدید.
        side: 'BUY' or 'SELL'
        order_type: 'MARKET', 'LIMIT', 'STOP', 'STOP_LIMIT'
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: str, symbol: str, **kwargs) -> dict:
        """
        لغو یک سفارش.
        """
        pass

    @abstractmethod
    def get_order_status(self, order_id: str, symbol: str, **kwargs) -> dict:
        """
        بررسی وضعیت یک سفارش.
        """
        pass

    # متدهای دیگر مانند get_order_history, get_symbol_info و ... را می‌توان اینجا تعریف کرد