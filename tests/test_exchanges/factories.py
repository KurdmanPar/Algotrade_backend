# tests/test_exchanges/factories.py

import factory
from django.contrib.auth import get_user_model
from apps.exchanges.models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    OrderHistory,
    MarketDataCandle,
)
from apps.bots.models import TradingBot # فرض بر این است که مدل وجود دارد و می‌توانید از آن استفاده کنید
from apps.core.encryption import encrypt_field # فرض بر این است که تابع رمزنگاری وجود دارد

User = get_user_model()

class ExchangeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exchange

    name = factory.Faker('company')
    code = factory.Sequence(lambda n: f'EXCH{n:03d}')
    type = factory.Faker('random_element', elements=[choice[0] for choice in Exchange.EXCHANGE_TYPE_CHOICES])
    base_url = factory.Faker('url')
    is_active = True
    is_sandbox = False
    rate_limit_per_second = 10


class ExchangeAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExchangeAccount

    user = factory.SubFactory('tests.test_accounts.factories.CustomUserFactory') # فرض بر این است که اکانت کاربری از قبل وجود دارد
    exchange = factory.SubFactory(ExchangeFactory)
    label = factory.Faker('word')
    # رمزنگاری کلیدها در هنگام ساخت
    api_key = 'test_api_key_12345' # این مقدار باید در setter ذخیره شود
    api_secret = 'test_api_secret_67890' # این مقدار باید در setter ذخیره شود

    # توجه: این فیلد فقط برای ساختار factory است، مقدار واقعی در مدل ذخیره نمی‌شود
    # ما باید بعداً مقدار را به صورت رمزنگاری شده در مدل ذخیره کنیم
    # یا مستقیماً در factory، رمزنگاری را انجام دهیم.

    # برای سادگی، فرض می‌کنیم که فیلدهای خصوصی رمزنگاری شده را مستقیماً پر می‌کنیم
    _api_key_encrypted = factory.LazyAttribute(lambda obj: encrypt_field(obj.api_key)[0])
    _api_secret_encrypted = factory.LazyAttribute(lambda obj: encrypt_field(obj.api_secret)[0])
    encrypted_key_iv = factory.LazyAttribute(lambda obj: encrypt_field(obj.api_key)[1])

    is_active = True
    is_paper_trading = False

    @factory.post_generation
    def linked_bots(self, create, extracted, **kwargs):
        if not create:
            return
        if extracted:
            for bot in extracted:
                self.linked_bots.add(bot)


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    wallet_type = factory.Faker('random_element', elements=[choice[0] for choice in Wallet.WALLET_TYPE_CHOICES])
    is_default = False
    leverage = factory.Faker('pydecimal', positive=True, max_digits=5, decimal_places=2, min_value=1, max_value=125)


class WalletBalanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WalletBalance

    wallet = factory.SubFactory(WalletFactory)
    asset_symbol = factory.Faker('lexify', text='????')
    total_balance = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    available_balance = factory.LazyAttribute(lambda obj: obj.total_balance * factory.Faker('pydecimal', positive=True, right_digits=0, max_value=1))


class AggregatedPortfolioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AggregatedPortfolio

    user = factory.SubFactory('tests.test_accounts.factories.CustomUserFactory') # فرض بر این است که اکانت کاربری از قبل وجود دارد
    base_currency = 'USD'
    total_equity = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=8)


class AggregatedAssetPositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AggregatedAssetPosition

    aggregated_portfolio = factory.SubFactory(AggregatedPortfolioFactory)
    asset_symbol = factory.Faker('lexify', text='????')
    total_quantity = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)


class OrderHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderHistory

    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    order_id = factory.Sequence(lambda n: f'order{n:06d}')
    symbol = factory.Faker('lexify', text='????')
    side = factory.Faker('random_element', elements=[choice[0] for choice in OrderHistory.SIDE_CHOICES])
    order_type = factory.Faker('random_element', elements=[choice[0] for choice in OrderHistory.ORDER_TYPE_CHOICES])
    status = factory.Faker('random_element', elements=[choice[0] for choice in OrderHistory.STATUS_CHOICES])
    price = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    quantity = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    time_placed = factory.Faker('date_time_this_decade', tzinfo=timezone.utc)
    time_updated = factory.LazyAttribute(lambda obj: obj.time_placed)


class MarketDataCandleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataCandle

    exchange = factory.SubFactory(ExchangeFactory)
    symbol = factory.Faker('lexify', text='????')
    interval = factory.Faker('random_element', elements=[choice[0] for choice in MarketDataCandle.INTERVAL_CHOICES])
    open_time = factory.Faker('date_time_this_decade', tzinfo=timezone.utc)
    open = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    high = factory.LazyAttribute(lambda obj: obj.open * factory.Faker('pydecimal', positive=True, right_digits=0, min_value=1.001, max_value=1.05))
    low = factory.LazyAttribute(lambda obj: obj.open * factory.Faker('pydecimal', positive=True, right_digits=0, min_value=0.95, max_value=0.999))
    close = factory.LazyAttribute(lambda obj: (obj.high + obj.low) / 2)
    volume = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    close_time = factory.LazyAttribute(lambda obj: obj.open_time + timedelta(minutes=1 if obj.interval == '1m' else 0))
