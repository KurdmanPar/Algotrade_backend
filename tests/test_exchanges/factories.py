# tests/test_exchanges/factories.py

import factory
from django.utils import timezone
from decimal import Decimal
from apps.accounts.factories import CustomUserFactory # import از اپلیکیشن دیگر
from apps.bots.factories import TradingBotFactory # import از اپلیکشن دیگر (اگر وجود داشت)
from apps.exchanges.models import (
    Exchange,
    ExchangeAccount,
    Wallet,
    WalletBalance,
    AggregatedPortfolio,
    AggregatedAssetPosition,
    OrderHistory,
    MarketDataCandle,
    # سایر مدل‌های اپلیکیشن exchanges
    # InstrumentGroup,
    # InstrumentCategory,
    # Instrument,
    # InstrumentExchangeMap,
    # IndicatorGroup,
    # Indicator,
    # IndicatorParameter,
    # IndicatorTemplate,
    # PriceActionPattern,
    # SmartMoneyConcept,
    # AIMetric,
    # InstrumentWatchlist,
)

# --- Factoryها برای مدل‌های اپلیکیشن exchanges ---

class ExchangeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exchange

    name = factory.Faker('company')
    code = factory.Sequence(lambda n: f'EXCH{n:03d}') # e.g., EXCH001, EXCH002
    type = factory.Faker('random_element', elements=[choice[0] for choice in Exchange.EXCHANGE_TYPE_CHOICES])
    base_url = factory.Faker('url')
    ws_url = factory.Faker('url')
    api_docs_url = factory.Faker('url')
    is_active = True
    is_sandbox = False
    rate_limit_per_second = 1000
    fees_structure = factory.Dict({'maker': '0.001', 'taker': '0.001'})
    limits = factory.Dict({'max_orders_per_minute': 1000, 'max_price_change_percent': 5})


class ExchangeAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExchangeAccount

    # استفاده از CustomUserFactory از اپلیکیشن accounts
    owner = factory.SubFactory(CustomUserFactory) # تغییر: owner به جای user
    exchange = factory.SubFactory(ExchangeFactory)
    label = factory.Faker('word')

    # رمزنگاری کلیدها در هنگام ساخت
    # توجه: این فقط مقدار داده می‌شود. در مدل، از propertyها برای رمزنگاری/رمزگشایی استفاده می‌شود
    api_key = 'test_api_key_12345'
    api_secret = 'test_api_secret_67890'
    # فرض: فیلدهای _api_key_encrypted و _api_secret_encrypted در مدل ذخیره می‌شوند
    # ما در اینجا فقط مقدار داده می‌دهیم و منیجر/متد ذخیره مدل مسئول رمزنگاری است
    # بنابراین، مستقیماً در فیلد مدل مقدار دهیم
    # اما چون این فیلدها رمزنگاری شده هستند، ممکن است نیاز به دستکاری داشته باشیم
    # روش معمول: فقط فیلد اصلی (مثل api_key) را در validated_data قرار دهیم و از setter در مدل استفاده کنیم
    # در Factory، اگر فیلدهای رمزنگاری شده مستقیماً وجود داشتند، باید آن‌ها را پر کنیم
    # فرض: فیلدهای رمزنگاری شده در مدل وجود دارند
    # اینجا فقط فیلدهای مسک شده را پر می‌کنیم یا مقدار رمزنگاری شده را مستقیماً قرار می‌دهیم
    # روش بهتر: استفاده از post_generation یا override کردن _create یا save
    # روش پیشنهادی: استفاده از post_generation یا override کردن save
    # یا فقط مقدار رمزنگاری شده را مستقیماً قرار دهیم (اگر از قبل داشته باشیم)
    # اینجا، فقط مقدار خام را در فیلد مربوطه قرار می‌دهیم و فرض می‌کنیم مدل آن را رمزنگاری می‌کند
    # اما چون فیلدهای رمزنگاری شده هستند، نمی‌توانیم مستقیماً api_key را قرار دهیم
    # بنابراین، فرض می‌کنیم که فیلدهای _api_key_encrypted و _api_secret_encrypted و encrypted_key_iv وجود دارند
    # و ما مقدار رمزنگاری شده و IV را قرار می‌دهیم
    # برای سادگی در تست، می‌توانیم از مقدار ثابت استفاده کنیم یا از تابع رمزنگاری استفاده کنیم
    # اما تابع رمزنگاری ممکن است نیاز به کلید سیستمی داشته باشد
    # بنابراین، مقدارهای رمزنگاری شده را موقتاً به صورت ثابت قرار می‌دهیم
    # فرض: ما یک کلید ثابت برای تست داریم یا فیلد را فقط مقداردهی می‌کنیم و مدل آن را رمزنگاری می‌کند (که نیازمند تغییر در مدل است)
    # برای اینجا، فرض می‌کنیم مدل از طریق propertyها رمزنگاری می‌کند و ما فقط مقدار اصلی را در validated_data قرار می‌دهیم
    # بنابراین، در Factory، فقط مقدار رمزنگاری شده را قرار می‌دهیم
    # روش: استفاده از post_generation
    _api_key_encrypted = factory.PostGenerationMethodCall('encrypt_field', 'test_api_key_12345')
    _api_secret_encrypted = factory.PostGenerationMethodCall('encrypt_field', 'test_api_secret_67890')
    encrypted_key_iv = factory.PostGenerationMethodCall('generate_iv')

    # یا مقدارهای ثابت رمزنگاری شده (برای سادگی تست، اگر رمزنگاری در مدل پیچیده نباشد)
    # _api_key_encrypted = "gAAAAAB..."
    # _api_secret_encrypted = "gAAAAAB..."
    # encrypted_key_iv = "some_iv..."

    extra_credentials = factory.Dict({'endpoint': 'https://api.example.com'})
    is_active = True
    is_paper_trading = False
    last_sync_at = factory.LazyFunction(timezone.now)
    last_login_ip = factory.Faker('ipv4')
    created_ip = factory.Faker('ipv4')
    account_info = factory.Dict({'canTrade': True, 'canWithdraw': True})
    trading_permissions = factory.Dict({'can_place_orders': True, 'can_cancel_orders': True})

    @factory.post_generation
    def linked_bots(self, create, extracted, **kwargs):
        """
        Allows linking bots to the account after creation.
        Usage: ExchangeAccountFactory(linked_bots=(bot1, bot2))
        """
        if not create:
            return
        if extracted:
            for bot in extracted:
                self.linked_bots.add(bot)

    # منیجرهای مدل احتمالاً در apps/core/managers.py یا apps/exchanges/managers.py تعریف شده‌اند
    # فرض: منیجر مدل ExchangeAccount از CoreOwnedModelManager ارث می‌برد که خود از BaseOwnedModelManager ارث می‌برد
    # و BaseOwnedModelManager از BaseManager ارث می‌برد
    # و BaseManager از models.Manager ارث می‌برد
    # و BaseOwnedModelManager یا CoreOwnedModelManager در Meta مدل قرار دارد
    # objects = CoreOwnedModelManager()


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    wallet_type = factory.Faker('random_element', elements=[choice[0] for choice in Wallet.WALLET_TYPE_CHOICES])
    description = factory.Faker('sentence')
    is_default = False
    is_margin_enabled = False
    leverage = Decimal('1')
    borrowed_amount = Decimal('0')

    # فرض: منیجر مدل Wallet از BaseManager ارث می‌برد
    # objects = BaseManager()


class WalletBalanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WalletBalance

    wallet = factory.SubFactory(WalletFactory)
    asset_symbol = factory.Faker('lexify', text='???')
    total_balance = factory.Faker('pydecimal', positive=True, max_digits=20, decimal_places=8)
    available_balance = factory.LazyAttribute(lambda obj: obj.total_balance * Decimal('0.9')) # 90% موجود
    in_order_balance = factory.LazyAttribute(lambda obj: obj.total_balance * Decimal('0.05')) # 5% در سفارش
    frozen_balance = factory.LazyAttribute(lambda obj: obj.total_balance * Decimal('0.05')) # 5% فریز
    borrowed_balance = Decimal('0')

    # فرض: منیجر مدل WalletBalance از BaseManager ارث می‌برد
    # objects = BaseManager()


class AggregatedPortfolioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AggregatedPortfolio

    # استفاده از CustomUserFactory از اپلیکیشن accounts
    owner = factory.SubFactory(CustomUserFactory) # تغییر: owner به جای user
    base_currency = 'USD'
    total_equity = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=8)
    total_unrealized_pnl = factory.Faker('pydecimal', max_digits=32, decimal_places=8) # ممکن است منفی باشد
    total_realized_pnl = factory.Faker('pydecimal', max_digits=32, decimal_places=8)
    total_pnl_percentage = factory.Faker('pydecimal', max_digits=8, decimal_places=4)
    total_commission_paid = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=8)
    total_funding_fees = factory.Faker('pydecimal', max_digits=32, decimal_places=8)
    last_valuation_at = factory.LazyFunction(timezone.now)

    # فرض: منیجر مدل AggregatedPortfolio از CoreOwnedModelManager ارث می‌برد
    # objects = CoreOwnedModelManager()


class AggregatedAssetPositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AggregatedAssetPosition

    aggregated_portfolio = factory.SubFactory(AggregatedPortfolioFactory)
    asset_symbol = factory.Faker('lexify', text='???')
    total_quantity = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    total_value_in_base_currency = factory.LazyAttribute(lambda obj: obj.total_quantity * Decimal('50000')) # فرض قیمت 50000
    per_exchange_breakdown = factory.Dict({'binance': {'quantity': '1.0', 'value': '50000'}, 'coinbase': {'quantity': '0.5', 'value': '25000'}})

    # فرض: منیجر مدل AggregatedAssetPosition از BaseManager ارث می‌برد
    # objects = BaseManager()


class OrderHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = OrderHistory

    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    order_id = factory.Sequence(lambda n: f'order{n:06d}')
    symbol = factory.Faker('lexify', text='???')
    side = factory.Faker('random_element', elements=[choice[0] for choice in OrderHistory.SIDE_CHOICES])
    order_type = factory.Faker('random_element', elements=[choice[0] for choice in OrderHistory.ORDER_TYPE_CHOICES])
    status = factory.Faker('random_element', elements=[choice[0] for choice in OrderHistory.STATUS_CHOICES])
    price = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    quantity = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    executed_quantity = factory.LazyAttribute(lambda obj: obj.quantity if obj.status == 'FILLED' else obj.quantity / 2)
    cumulative_quote_qty = factory.LazyAttribute(lambda obj: obj.price * obj.executed_quantity)
    time_placed = factory.LazyFunction(timezone.now)
    time_updated = factory.LazyFunction(timezone.now)
    commission = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    commission_asset = 'BNB' # یا یک ارز دیگر

    # ارتباط با بات (اختیاری)
    trading_bot = factory.SubFactory(TradingBotFactory) # اگر فکتوری وجود داشت

    # فرض: منیجر مدل OrderHistory از BaseManager ارث می‌برد
    # objects = BaseManager()


class MarketDataCandleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = MarketDataCandle

    exchange = factory.SubFactory(ExchangeFactory)
    symbol = factory.Faker('lexify', text='???')
    interval = factory.Faker('random_element', elements=[choice[0] for choice in MarketDataCandle.INTERVAL_CHOICES])
    open_time = factory.LazyFunction(timezone.now)
    open = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    high = factory.LazyAttribute(lambda obj: obj.open * Decimal('1.02')) # 2% بالاتر
    low = factory.LazyAttribute(lambda obj: obj.open * Decimal('0.98'))  # 2% پایین‌تر
    close = factory.LazyAttribute(lambda obj: (obj.high + obj.low) / 2) # میانگین
    volume = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    close_time = factory.LazyAttribute(lambda obj: obj.open_time + timezone.timedelta(minutes=1) if obj.interval == '1m' else obj.open_time) # ساده
    quote_asset_volume = factory.LazyAttribute(lambda obj: obj.close * obj.volume)
    number_of_trades = factory.Faker('pyint', min_value=10, max_value=1000)
    taker_buy_base_asset_volume = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)
    taker_buy_quote_asset_volume = factory.Faker('pydecimal', positive=True, max_digits=32, decimal_places=16)

    # فرض: منیجر مدل MarketDataCandle از BaseManager ارث می‌برد
    # objects = BaseManager()

# --- سایر Factoryها ---
# می‌توانید برای سایر مدل‌هایی که در exchanges/models.py تعریف می‌کنید نیز Factory بنویسید
# مثلاً:
# class InstrumentGroupFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = InstrumentGroup
#     name = factory.Faker('word')
#     description = factory.Faker('sentence')
#
# class InstrumentCategoryFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = InstrumentCategory
#     name = factory.Faker('word')
#     description = factory.Faker('sentence')
#     supports_leverage = factory.Faker('boolean')
#     supports_shorting = factory.Faker('boolean')
#
# class InstrumentFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Instrument
#     symbol = factory.Faker('lexify', text='???')
#     name = factory.Faker('name')
#     group = factory.SubFactory(InstrumentGroupFactory)
#     category = factory.SubFactory(InstrumentCategoryFactory)
#     base_asset = factory.Faker('lexify', text='???')
#     quote_asset = factory.Faker('lexify', text='???')
#     # ... سایر فیلدها
#
# class InstrumentExchangeMapFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = InstrumentExchangeMap
#     instrument = factory.SubFactory(InstrumentFactory)
#     exchange = factory.SubFactory(ExchangeFactory)
#     exchange_symbol = factory.LazyAttribute(lambda obj: obj.instrument.symbol) # یا متفاوت
#     # ... سایر فیلدها
#
# class IndicatorGroupFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = IndicatorGroup
#     name = factory.Faker('word')
#     description = factory.Faker('sentence')
#
# class IndicatorFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = Indicator
#     name = factory.Faker('word')
#     code = factory.LazyAttribute(lambda obj: obj.name.upper())
#     group = factory.SubFactory(IndicatorGroupFactory)
#     description = factory.Faker('sentence')
#     # ... سایر فیلدها
#
# class IndicatorParameterFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = IndicatorParameter
#     indicator = factory.SubFactory(IndicatorFactory)
#     name = factory.Faker('word')
#     display_name = factory.Faker('sentence')
#     data_type = factory.Faker('random_element', elements=[choice[0] for choice in IndicatorParameter.DATA_TYPE_CHOICES])
#     default_value = factory.Faker('word')
#     # ... سایر فیلدها
#
# class IndicatorTemplateFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = IndicatorTemplate
#     name = factory.Faker('word')
#     description = factory.Faker('sentence')
#     indicator = factory.SubFactory(IndicatorFactory)
#     parameters = factory.Dict({'period': 14})
#     # ... سایر فیلدها
#
# class PriceActionPatternFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = PriceActionPattern
#     name = factory.Faker('word')
#     code = factory.LazyAttribute(lambda obj: obj.name.upper())
#     description = factory.Faker('sentence')
#     is_active = True
#
# class SmartMoneyConceptFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = SmartMoneyConcept
#     name = factory.Faker('word')
#     code = factory.LazyAttribute(lambda obj: obj.name.upper())
#     description = factory.Faker('sentence')
#     is_active = True
#
# class AIMetricFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = AIMetric
#     name = factory.Faker('word')
#     code = factory.LazyAttribute(lambda obj: obj.name.upper())
#     description = factory.Faker('sentence')
#     data_type = 'float'
#     is_active = True
#
# class InstrumentWatchlistFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = InstrumentWatchlist
#     owner = factory.SubFactory(CustomUserFactory) # تغییر: owner به جای user
#     name = factory.Faker('word')
#     description = factory.Faker('sentence')
#     is_public = factory.Faker('boolean')
#     # ... سایر فیلدها

logger.info("Exchanges factories loaded successfully.")
