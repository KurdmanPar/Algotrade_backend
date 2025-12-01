# apps/connectors/registry.py
_CONNECTORS = {}

def register_connector(name: str):
    def decorator(cls):
        _CONNECTORS[name.upper()] = cls
        return cls
    return decorator

def get_connector(name: str):
    return _CONNECTORS.get(name.upper())

# ثبت کانکتورها
from .nobitex_connector import NobitexConnector
from .lbank_connector import LBankConnector
from .binance_connector import BinanceConnector # فرض کنید وجود دارد

register_connector('NOBITEX')(NobitexConnector)
register_connector('LBANK')(LBankConnector)
register_connector('BINANCE')(BinanceConnector)
# ...