# tests/integration/test_order_flow.py
import pytest
from django.contrib.auth import get_user_model
from apps.trading.models import Order
from apps.signals.models import Signal
from tests.factories.trading_factories import OrderFactory
from tests.factories.signals_factories import SignalFactory
from tests.factories.bots_factories import BotFactory  # فقط در اینجا import کنید
from tests.factories.strategies_factories import StrategyVersionFactory

User = get_user_model()

@pytest.mark.django_db(transaction=True)
def test_signal_creates_order_integration():
    # ایجاد وابستگی‌ها به صورت دستی برای جلوگیری از چرخه
    bot = BotFactory()
    strategy_version = StrategyVersionFactory()

    signal = SignalFactory(
        user=bot.owner,  # فرض بر این است که bot دارای owner است
        bot=bot,
        strategy_version=strategy_version,
        status="APPROVED",
        direction="BUY",
        quantity=1.0,
        price=50000.0
    )

    order = OrderFactory(
        user=signal.user,
        exchange_account=bot.exchange_account,
        instrument=signal.instrument,
        side=signal.direction,
        order_type="MARKET",
        quantity=signal.quantity,
        price=signal.price,
        status="PENDING",
        client_order_id=f"sig_{signal.id}_order",
        correlation_id=signal.correlation_id
    )

    assert order is not None
    assert order.user == signal.user
    assert order.instrument == signal.instrument
    assert order.quantity == signal.quantity
    assert order.correlation_id == signal.correlation_id

    print("✅ تست ادغام سیگنال و سفارش با موفقیت انجام شد.")