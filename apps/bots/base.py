# apps/bots/base.py
"""
Base class for all exchange connectors.
This class defines the interface (contract) that every specific exchange connector (e.g., BinanceConnector) must implement.
It ensures that all connectors behave consistently.
"""
from abc import ABC, abstractmethod

class ExchangeConnector(ABC):
    """
    کلاس پایه انتزاعی (Abstract Base Class) که نقشه راه (Interface)
    را برای تمام اتصال‌دهنده‌های صرافی تعریف می‌کند.
    هر اتصال‌دهنده صرافی (مثل BinanceConnector) باید این قرارداد را پیاده‌سازی کند.
    این کار باعث می‌شود که تمام اتصال‌دهنده‌ها رفتار یکسانی داشته باشند.
    """
    def __init__(self, api_key: str, api_secret: str, **kwargs):
        """
        سازنده کلاس برای ذخیره کلیدهای API.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.passphrase = kwargs.get('passphrase')

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
        """
        pass

    @abstractmethod
    def cancel_order(self, order_id: متغیر, symbol: str, **kwargs) -> dict:
        """
        لغو یک سفارش.
        """
        pass

    # متدهای دیگر مانند get_order_status, get_order_history, get_symbol_info, get_open_positions و ...