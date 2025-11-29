# apps/connectors/registry.py

_CONNECTORS = {}

def register_connector(exchange_code: str):
    """
    دکوریتور برای ثبت یک کلاس کانکتور.
    """
    def decorator(cls):
        _CONNECTORS[exchange_code.upper()] = cls
        return cls
    return decorator

def get_connector(exchange_code: str):
    """
    دریافت کلاس کانکتور بر اساس کد صرافی.
    """
    return _CONNECTORS.get(exchange_code.upper())

def list_registered_connectors():
    """
    لیست تمام کانکتورهای ثبت شده.
    """
    return list(_CONNECTORS.keys())