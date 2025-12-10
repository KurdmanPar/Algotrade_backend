# tests/factories.py

import factory
from django.utils import timezone
from datetime import timedelta
from apps.accounts.models import CustomUser, UserProfile, UserSession, UserAPIKey

class CustomUserFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating CustomUser instances.
    """
    class Meta:
        model = CustomUser

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    username_display = factory.Faker('user_name')
    user_type = 'individual'
    is_verified = True
    is_active = True
    is_demo = True

    # Traits are a powerful feature to create variations of the object
    @factory.post_generation
    def password(obj, create, extracted, **kwargs):
        password = extracted or factory.Faker('password')
        obj.set_password(password)

    class Params:
        # Trait to create a superuser
        superuser = factory.Trait(
            is_staff=True,
            is_superuser=True,
        )
        # Trait to create a locked user
        locked = factory.Trait(
            is_locked=True,
            failed_login_attempts=5,
            locked_until=timezone.now() + timedelta(minutes=30)
        )
        # Trait to create an institutional user
        institutional = factory.Trait(
            user_type='institutional'
        )

class UserProfileFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating UserProfile instances.
    It automatically creates a user if one is not provided.
    """
    class Meta:
        model = UserProfile

    user = factory.SubFactory(CustomUserFactory)
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    display_name = factory.Faker('user_name')
    phone_number = factory.Faker('phone_number')
    preferred_base_currency = "IRT"
    risk_level = 'medium'
    two_factor_enabled = False

    class Params:
        # Trait to create a KYC verified profile
        kyc_verified = factory.Trait(
            is_kyc_verified=True,
            kyc_document_type='PASSPORT',
            kyc_document_number=factory.Faker('ssn'),
            kyc_submitted_at=timezone.now() - timedelta(days=5),
            kyc_verified_at=timezone.now() - timedelta(days=1),
        )

class UserSessionFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating UserSession instances.
    """
    class Meta:
        model = UserSession

    user = factory.SubFactory(CustomUserFactory)
    session_key = factory.Faker('uuid4')
    ip_address = factory.Faker('ipv4')
    user_agent = factory.Faker('user_agent')
    is_active = True
    expires_at = factory.LazyAttribute(lambda o: timezone.now() + timedelta(days=30))

class UserAPIKeyFactory(factory.django.DjangoModelFactory):
    """
    Factory for creating UserAPIKey instances.
    """
    class Meta:
        model = UserAPIKey

    user = factory.SubFactory(CustomUserFactory)
    name = factory.Faker('word')
    is_active = True
    permissions = {'read': True, 'trade': False}