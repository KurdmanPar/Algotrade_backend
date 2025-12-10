# tests/factories/exchanges_factories.py
import factory
from apps.exchanges.models import (
    Exchange, ExchangeAccount, Wallet, WalletBalance, AggregatedPortfolio, AggregatedAssetPosition
)
from tests.factories.accounts_factories import UserFactory


class ExchangeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Exchange

    name = factory.Sequence(lambda n: f"Exchange {n}")
    code = factory.LazyAttribute(lambda obj: obj.name.replace(" ", "").upper())
    type = factory.Iterator(["CRYPTO", "STOCK", "FOREX"])
    base_url = factory.Faker("url")
    ws_url = factory.Faker("url")
    is_active = factory.Faker("boolean")
    rate_limit_per_minute = factory.Faker("pyint", min_value=100, max_value=5000)
    fees_structure = factory.Dict({"taker": 0.001, "maker": 0.0005})
    limits = factory.Dict({"max_order_size": 1000000})


class ExchangeAccountFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ExchangeAccount

    user = factory.SubFactory(UserFactory)
    exchange = factory.SubFactory(ExchangeFactory)
    label = factory.Sequence(lambda n: f"Account {n}")
    api_key_encrypted = factory.Faker("password")
    api_secret_encrypted = factory.Faker("password")
    extra_credentials = factory.Dict({})
    is_active = factory.Faker("boolean")
    last_sync_at = factory.Faker("date_time_this_month", tzinfo=None)
    last_login_ip = factory.Faker("ipv4")
    created_ip = factory.Faker("ipv4")


class WalletFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Wallet

    exchange_account = factory.SubFactory(ExchangeAccountFactory)
    wallet_type = factory.Iterator(["SPOT", "FUTURES", "MARGIN", "ISOLATED_MARGIN", "FUNDING", "OTHER"])
    description = factory.Faker("sentence")
    is_default = factory.Faker("boolean")
    leverage = factory.Faker("pydecimal", max_digits=5, decimal_places=2, default=1)
    borrowed_amount = factory.Faker("pydecimal", max_digits=32, decimal_places=16, default=0)


class WalletBalanceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WalletBalance

    wallet = factory.SubFactory(WalletFactory)
    asset_symbol = factory.Faker("currency_code")
    total_balance = factory.Faker("pydecimal", left_digits=32, right_digits=16, default=0)
    available_balance = factory.Faker("pydecimal", left_digits=32, right_digits=16, default=0)
    in_order_balance = factory.Faker("pydecimal", left_digits=32, right_digits=16, default=0)
    frozen_balance = factory.Faker("pydecimal", left_digits=32, right_digits=16, default=0)
    borrowed_balance = factory.Faker("pydecimal", left_digits=32, right_digits=16, default=0)


class AggregatedPortfolioFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AggregatedPortfolio

    user = factory.SubFactory(UserFactory)
    base_currency = factory.Faker("currency_code")
    total_equity = factory.Faker("pydecimal", left_digits=32, decimal_places=8, default=0)
    total_unrealized_pnl = factory.Faker("pydecimal", left_digits=32, decimal_places=8, default=0)
    total_realized_pnl = factory.Faker("pydecimal", left_digits=32, decimal_places=8, default=0)
    total_pnl_percentage = factory.Faker("pydecimal", max_digits=8, decimal_places=4, default=0)
    total_commission_paid = factory.Faker("pydecimal", left_digits=32, decimal_places=8, default=0)
    total_funding_fees = factory.Faker("pydecimal", left_digits=32, decimal_places=8, default=0)
    last_valuation_at = factory.Faker("date_time_this_month", tzinfo=None)


class AggregatedAssetPositionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AggregatedAssetPosition

    aggregated_portfolio = factory.SubFactory(AggregatedPortfolioFactory)
    asset_symbol = factory.Faker("currency_code")
    total_quantity = factory.Faker("pydecimal", left_digits=32, decimal_places=16, default=0)
    total_value_in_base_currency = factory.Faker("pydecimal", left_digits=32, decimal_places=8, default=0)
    per_exchange_breakdown = factory.Dict({"exchange1": 100, "exchange2": 200})