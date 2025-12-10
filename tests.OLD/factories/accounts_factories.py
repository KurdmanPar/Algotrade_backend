# tests/factories/accounts_factories.py
import factory
from django.contrib.auth import get_user_model
from apps.accounts.models import UserProfile

User = get_user_model()

class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username_display = factory.LazyAttribute(lambda obj: f"User_{obj.email.split('@')[0]}")
    user_type = factory.Iterator(["INDIVIDUAL", "INSTITUTIONAL", "DEVELOPER"])
    is_verified = factory.Faker("boolean")
    is_active = factory.Faker("boolean")
    is_demo = factory.Faker("boolean")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Override the default _create method to use create_user for hashing passwords."""
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class UserProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = UserProfile

    user = factory.SubFactory(UserFactory)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    phone_number = factory.Faker("phone_number")
    nationality = factory.Faker("country_code")
    date_of_birth = factory.Faker("date_of_birth")
    address = factory.Faker("address")
    preferred_base_currency = factory.Faker("currency_code")
    default_leverage = factory.Faker("pyint", min_value=1, max_value=100)
    risk_level = factory.Iterator(["LOW", "MEDIUM", "HIGH"])
    max_active_trades = factory.Faker("pyint", min_value=1, max_value=20)
    max_capital = factory.Faker("pydecimal", left_digits=12, right_digits=8, positive=True)
    notify_on_trade = factory.Faker("boolean")
    notify_on_balance_change = factory.Faker("boolean")
    notify_on_risk_limit_breach = factory.Faker("boolean")
    is_kyc_verified = factory.Faker("boolean")
    kyc_document_type = factory.Iterator(["PASSPORT", "ID_CARD", "DRIVERS_LICENSE"])
    kyc_document_number = factory.Faker("bothify", text="?#########")
    kyc_submitted_at = factory.Faker("date_time_this_month", tzinfo=None)
    kyc_verified_at = factory.Faker("date_time_this_month", tzinfo=None)