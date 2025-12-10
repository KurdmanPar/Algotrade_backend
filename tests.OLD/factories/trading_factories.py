# tests/factories/trading_factories.py
import factory
from apps.trading.models import Order, Trade, Position, OrderLog
from tests.factories.accounts_factories import UserFactory
from tests.factories.exchanges_factories import ExchangeAccountFactory
from tests.factories.instruments_factories import InstrumentFactory
# از bots_factories اینجا import نکنید
# from tests.factories.bots_factories import BotFactory

class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Order

    user = factory.SubFactory(UserFactory)
    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    instrument = factory.SubFactory(InstrumentFactory)

    # اینجا هم نباید BotFactory import شود
    # bot = factory.SubFactory(BotFactory)

    side = factory.Iterator(["BUY", "SELL"])
    order_type = factory.Iterator([
        "MARKET", "LIMIT", "STOP", "STOP_LIMIT", "TAKE_PROFIT", "TAKE_PROFIT_LIMIT", "TRAILING_STOP"
    ])
    quantity = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    price = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    status = factory.Iterator(["PENDING", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "EXPIRED"])
    client_order_id = factory.Sequence(lambda n: f"client_order_{n}")
    exchange_order_id = factory.Sequence(lambda n: f"exchange_order_{n}")
    commission_paid = factory.Faker("pydecimal", left_digits=6, right_digits=8, positive=True)
    stop_loss_price = factory.Faker("pydecimal", left_digits=12, right_digits=8, allow_nan=True)
    take_profit_price = factory.Faker("pydecimal", left_digits=12, right_digits=8, allow_nan=True)
    correlation_id = factory.Faker("uuid4", cast_to=str)

class TradeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Trade

    order = factory.SubFactory(OrderFactory)
    trade_id = factory.Sequence(lambda n: f"trade_{n}")
    price = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    quantity = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    fee = factory.Faker("pydecimal", left_digits=6, right_digits=8, positive=True)
    fee_asset = factory.Faker("currency_code")
    executed_at = factory.Faker("date_time_this_month", tzinfo=None)

class PositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Position

    user = factory.SubFactory(UserFactory)
    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    instrument = factory.SubFactory(InstrumentFactory)

    # bot = factory.SubFactory(BotFactory)  # نباید اینجا باشد
    # strategy_version = factory.SubFactory(StrategyVersionFactory)  # نباید اینجا باشد

    side = factory.Iterator(["LONG", "SHORT"])
    quantity = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    avg_entry_price = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    leverage = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True, min_value=1, max_value=100)
    liquidation_price = factory.Faker("pydecimal", left_digits=12, right_digits=8, allow_nan=True)
    margin_used = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    unrealized_pnl = factory.Faker("pydecimal", left_digits=10, right_digits=8, allow_nan=True)
    realized_pnl = factory.Faker("pydecimal", left_digits=10, right_digits=8, allow_nan=True)
    opened_at = factory.Faker("date_time_this_month", tzinfo=None)
    closed_at = factory.Faker("date_time_between", start_date="+1d", end_date="+30d", tzinfo=None)
    status = factory.Iterator(["OPEN", "CLOSED"])

class OrderLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderLog

    order = factory.SubFactory(OrderFactory)
    old_status = factory.Iterator(["PENDING", "PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED"])
    new_status = factory.Iterator(["PARTIALLY_FILLED", "FILLED", "CANCELED", "REJECTED", "PENDING"])
    message = factory.Faker("sentence")
    details = factory.Dict({"extra": "info"})