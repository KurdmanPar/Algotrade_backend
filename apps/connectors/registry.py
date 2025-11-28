# apps/connectors/registry.py
from .binance_connector import BinanceConnector
# از سایر اتصال‌دهنده‌ها اینجا import کنید
# from .coinbase_connector import CoinbaseConnector
# from .kraken_connector import KrakenConnector

CONNECTOR_REGISTRY = {
    # 'BINANCE': BinanceConnector,
    # # 'COINBASE': CoinbaseConnector,
    # # 'KRAKEN': KrakenConnector,
    # # ...

    'BINANCE': 'apps.connectors.binance_connector.BinanceConnector',
    # 'COINBASE': 'apps.connectors.coinbase_connector.CoinbaseConnector',
    # ...
}

def get_connector(exchange_code: str):
    """
    با دریافت کد صرافی (مثلاً 'BINANCE')، نمونه کلاس اتصال‌دهنده مربوطه را برمی‌گرداند.
    """
    """Gets the connector class for a given exchange code."""
    connector_class = CONNECTOR_REGISTRY.get(exchange_code.upper())
    if not connector_class:
        raise ValueError(f"Unsupported exchange: {exchange_code}")
    return connector_class