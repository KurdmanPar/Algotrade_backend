# tests/factories/bots_factories.py
import factory
from apps.bots.models import Bot, BotStrategyConfig, BotLog, BotPerformanceSnapshot
from tests.factories.accounts_factories import UserFactory
from tests.factories.exchanges_factories import ExchangeAccountFactory
from tests.factories.instruments_factories import InstrumentFactory

class BotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Bot

    owner = factory.SubFactory(UserFactory)
    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    instrument = factory.SubFactory(InstrumentFactory)
    name = factory.Sequence(lambda n: f"Bot {n}")
    description = factory.Faker("sentence")
    bot_type = factory.Iterator(["BUY_ONLY", "SELL_ONLY", "LONG_SHORT", "GRID", "DCA"])
    status = factory.Iterator(["INACTIVE", "ACTIVE", "PAUSED", "STOPPED", "ERROR"])
    mode = factory.Iterator(["LIVE", "PAPER"])
    control_type = factory.Iterator(["MANUAL", "AUTOMATIC"])
    max_concurrent_trades = factory.Faker("pyint", min_value=1, max_value=10)
    max_position_size = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    max_total_capital = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    leverage = factory.Faker("pydecimal", left_digits=3, right_digits=2, positive=True, min_value=1, max_value=100)
    desired_profit_target_percent = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    max_allowed_loss_percent = factory.Faker("pydecimal", left_digits=4, right_digits=2, positive=True)
    trailing_stop_config = factory.Dict({"enabled": True, "activation_percent": 1.0, "trail_percent": 0.5})
    schedule_config = factory.Dict({"enabled": True, "times": ["09:00", "17:00"]})
    paper_trading_balance = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    is_paused_by_system = factory.Faker("boolean")
    performance_metrics = factory.Dict({"pnl": 0, "sharpe": 0, "max_drawdown": 0})


class BotStrategyConfigFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BotStrategyConfig

    bot = factory.SubFactory(BotFactory)
    # تا زمانی که در تست‌ها نیاز به آن نداشته باشیم، از SubFactory مستقیم خودداری می‌کنیم
    # در تست، می‌توانیم به صورت زیر ایجاد کنیم:
    # strategy_version = factory.SubFactory('tests.factories.strategies_factories.StrategyVersionFactory')
    # یا بهتر، در تست از `create` استفاده کنیم و `strategy_version` را خودمان بسازیم.

    # برای اکنون، فقط bot را ایجاد می‌کنیم
    # strategy_version را در تست‌ها به صورت دستی ست می‌کنیم
    # weight و سایر فیلدها را می‌توانیم مستقیماً در اینجا ایجاد کنیم
    weight = factory.Faker("pyfloat", min_value=0.1, max_value=1.0)
    priority = factory.Faker("pyint", min_value=0, max_value=10)
    is_primary = factory.Faker("boolean")
    is_active = factory.Faker("boolean")
    parameters_override = factory.Dict({"param1": 100, "param2": 200})
    last_execution_result = factory.Dict({"status": "success", "pnl": 100})

    # اگر می‌خواهیم در تست از SubFactory استفاده کنیم، می‌توانیم در تست بنویسیم:
    # bot = BotFactory()
    # strategy_version = StrategyVersionFactory()
    # config = BotStrategyConfigFactory(bot=bot, strategy_version=strategy_version)

class BotLogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BotLog

    bot = factory.SubFactory(BotFactory)
    level = factory.Iterator(["INFO", "WARNING", "ERROR"])
    message = factory.Faker("sentence")
    timestamp = factory.Faker("date_time_this_month", tzinfo=None)
    details = factory.Dict({"extra_info": "data"})

class BotPerformanceSnapshotFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BotPerformanceSnapshot

    bot = factory.SubFactory(BotFactory)
    period_start = factory.Faker("date_time_this_month", tzinfo=None)
    period_end = factory.LazyAttribute(lambda obj: obj.period_start + factory.Faker("timedelta", days=1))

    total_pnl = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    total_pnl_percentage = factory.Faker("pydecimal", left_digits=5, right_digits=4, positive=True)
    realized_pnl = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    unrealized_pnl = factory.Faker("pydecimal", left_digits=10, right_digits=8, positive=True)
    max_drawdown = factory.Faker("pydecimal", left_digits=5, right_digits=4, positive=True)
    sharpe_ratio = factory.Faker("pydecimal", left_digits=3, right_digits=6, allow_nan=True)
    total_trades = factory.Faker("pyint", min_value=0, max_value=1000)
    win_rate = factory.Faker("pydecimal", left_digits=5, right_digits=2, min_value=0, max_value=100, allow_nan=True)
    avg_trade_duration = factory.Faker("timedelta", days=0, hours=1, minutes=30)
    profit_factor = factory.Faker("pydecimal", left_digits=4, right_digits=6, allow_nan=True)