# apps/exchanges/templatetags/exchange_filters.py

from django import template
from django.utils.safestring import mark_safe
from apps.exchanges.models import ExchangeAccount
import logging

logger = logging.getLogger(__name__)
register = template.Library()

@register.filter
def exchange_status_badge(exchange_account: ExchangeAccount) -> str:
    """
    Creates an HTML badge representing the status of an exchange account.
    """
    if not isinstance(exchange_account, ExchangeAccount):
        logger.warning("exchange_status_badge filter called with non-ExchangeAccount object.")
        return mark_safe("<span class='badge badge-secondary'>Unknown</span>")

    status = exchange_account.status
    if status == 'SUBSCRIBED':
        css_class = 'badge-success'
    elif status == 'UNSUBSCRIBED':
        css_class = 'badge-warning'
    elif status == 'ERROR':
        css_class = 'badge-danger'
    else:
        css_class = 'badge-info' # PENDING

    return mark_safe(f"<span class='badge {css_class}'>{status.title()}</span>")

@register.filter
def format_currency(amount, currency_code='USD'):
    """
    Formats an amount with a currency symbol.
    """
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'IRT': '﷼',
        'IRT_N': 'تومان',
        # ... سایر ارزها ...
    }
    symbol = symbols.get(currency_code.upper(), currency_code)
    return f"{amount} {symbol}"
