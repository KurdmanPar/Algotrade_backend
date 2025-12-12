# tests/test_core/conftest.py

import pytest
from pytest_factoryboy import register
from .factories import (
    # ثبت تمام Factoryهای مربوط به اپلیکیشن core
    BaseModelFactory,
    BaseOwnedModelFactory,
    TimeStampedModelFactory,
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
    # سایر Factoryهایی که ممکن است در core تعریف شده باشند
    # InstrumentGroupFactory,
    # InstrumentCategoryFactory,
    # InstrumentFactory,
    # InstrumentExchangeMapFactory,
    # IndicatorGroupFactory,
    # IndicatorFactory,
    # IndicatorParameterFactory,
    # IndicatorTemplateFactory,
    # PriceActionPatternFactory,
    # SmartMoneyConceptFactory,
    # AIMetricFactory,
    # InstrumentWatchlistFactory,
)

# ثبت Factoryها به عنوان Fixture
register(BaseModelFactory)
register(BaseOwnedModelFactory)
register(TimeStampedModelFactory)
register(AuditLogFactory)
register(SystemSettingFactory)
register(CacheEntryFactory)
# register(InstrumentGroupFactory) # فقط اگر در core تعریف شده باشد
# register(InstrumentCategoryFactory) # فقط اگر در core تعریف شده باشد
# register(InstrumentFactory) # فقط اگر در core تعریف شده باشد
# register(InstrumentExchangeMapFactory) # فقط اگر در core تعریف شده باشد
# register(IndicatorGroupFactory) # فقط اگر در core تعریف شده باشد
# register(IndicatorFactory) # فقط اگر در core تعریف شده باشد
# register(IndicatorParameterFactory) # فقط اگر در core تعریف شده باشد
# register(IndicatorTemplateFactory) # فقط اگر در core تعریف شده باشد
# register(PriceActionPatternFactory) # فقط اگر در core تعریف شده باشد
# register(SmartMoneyConceptFactory) # فقط اگر در core تعریف شده باشد
# register(AIMetricFactory) # فقط اگر در core تعریف شده باشد
# register(InstrumentWatchlistFactory) # فقط اگر در core تعریف شده باشد

@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """
    اطمینان از دسترسی به پایگاه داده برای تمام تست‌ها.
    """
    pass

# --- fixtureهای دیگر ---
@pytest.fixture
def api_client():
    """
    Returns an API client instance for making requests.
    """
    from rest_framework.test import APIClient
    return APIClient()

@pytest.fixture
def authenticated_api_client(api_client, CustomUserFactory):
    """
    Returns an API client instance that is authenticated with a user.
    """
    user = CustomUserFactory()
    api_client.force_authenticate(user=user)
    return api_client, user # برگرداندن client و user برای دسترسی آسان در تست

# fixture برای سایر کلاس‌هایی که نیاز به آن‌ها دارید می‌توانید اینجا تعریف کنید
# مثلاً یک fixture برای سرویس‌های `core` یا یک fixture برای اتصال به کانکتور خاص
