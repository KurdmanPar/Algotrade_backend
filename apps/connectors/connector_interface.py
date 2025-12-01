# apps/connectors/connector_interface.py
from abc import ABC, abstractmethod
from typing import Dict, Any, AsyncGenerator


class IExchangeConnector(ABC):
    """
    رابط استاندارد برای تمام کانکتورهای صرافی.
    """
    @abstractmethod
    async def connect(self):
        pass

    @abstractmethod
    async def disconnect(self):
        pass

    @abstractmethod
    async def listen(self) -> AsyncGenerator[Dict[str, Any], None]:
        """
        یک جنریتور از داده‌های خام دریافتی.
        """
        pass

    @abstractmethod
    def get_historical_data(self, symbol: str, timeframe: str, start: str, end: str):
        pass

    @abstractmethod
    def subscribe(self, symbol: str, data_type: str):
        pass

    @abstractmethod
    def unsubscribe(self, symbol: str, data_type: str):
        pass