# apps/bots/connector_utils.py
from .base import ExchangeConnector
from apps.connectors.binance_connector import BinanceConnector
from apps.connectors.registry import get_connector


def get_bot_connector(bot_instance):
    """
    یک تابع کمکی برای دریافت کانکتور اتصال‌دهنده صحیح برای یک بات.
    """
    exchange_account = bot_instance.exchange_account
    connector_class = get_connector(exchange_code=exchange_account.exchange.code)
    if not connector_class:
        raise ValueError(f"Unsupported exchange: {exchange_account.exchange.code}")

    # ایجاد نمونه از کلاس اتصال‌دهنده با کلیدهای API رمزنگاری شده
    connector = connector_class(
        api_key=exchange_account.api_key_encrypted,
        api_secret=exchange_account.api_secret_encrypted
    )

    # اتصال به صرافی
    if connector.connect():
        return connector
    else:
        return None


