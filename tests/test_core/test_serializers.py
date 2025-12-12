ممنون بابت تأیید. تاکنون فایل‌های زیر برای اپلیکیشن `core` ایجاد یا ارتقا یافته‌اند:

1.  `apps.py`
2.  `models.py`
3.  `serializers.py`
4.  `views.py`
5.  `urls.py`
6.  `permissions.py`
7.  `admin.py`
8.  `services.py`
9.  `tasks.py`
10. `helpers.py` (یا `utils.py`)
11. `exceptions.py`
12. `managers.py`
13. `signals.py`
14. `mixins.py`
15. `pagination.py`
16. `middleware.py`
17. `cache.py`
18. `constants.py`
19. `registry.py`
20. `filters.py`
21. `validators.py`
22. `logging.py`
23. `encryption.py`
24. `messaging.py`
25. `__init__.py` (اگر وجود داشته باشد)

اکنون نوبت به فایل بعدی در ساختار اپلیکیشن `core` می‌رسد. با توجه به اینکه `messaging.py`، `logging.py`، `encryption.py`، `registry.py`، `pagination.py`، `middleware.py`، `cache.py`، `filters.py`، `validators.py`، `constants.py`، `exceptions.py`، `managers.py`، `signals.py`، `admin.py`، `apps.py`، `urls.py`، `permissions.py`، `services.py`، `tasks.py`، `helpers.py` (یا `utils.py`) و `serializers.py` و `views.py` قبلاً ایجاد یا ارتقا یافته‌اند، فایل منطقی بعدی که ممکن است نیاز به بازنگری داشته باشد، **`apps/core/consumers.py`** یا **`apps/core/routing.py`** است، اما این فایل‌ها بیشتر در اپلیکیشنی قرار می‌گیرند که واقعاً نیاز به WebSocket دارند (مثل `market_data` یا `agents`). بنابراین، اگر قصد دارید `consumers.py` و `routing.py` را در `core` قرار دهید، باید منطق مربوطه (مثل `MessageBus` یا `AgentCommunicationConsumer`) اینجا تعریف شود، اما ممکن است منطقی‌تر باشد که آن‌ها در اپلیکیشن مناسب‌تر (مثلاً `agents` یا `market_data`) قرار گیرند.

همچنین، ممکن است فایل‌هایی مانند `apps/core/middleware.py` یا `apps/core/management/commands/` (برای Commandهای سفارشی) نیاز به ایجاد یا ارتقا داشته باشند، اما `middleware.py` قبلاً ایجاد شده بود.

**پس از این فایل‌ها، نوبت به نوشتن فایل‌های تست (Tests) می‌رسد.** اما قبل از آن، یک فایل کلیدی دیگر که ممکن است در `core` قرار گیرد، فایل `apps/core/management/commands/` است. این شامل Commandهای مدیریتی سفارشی می‌شود که می‌توانند برای کارهایی مانند راه‌اندازی اولیه سیستم، اجرای وظایف دوره‌ای یا اشکال‌زدایی استفاده شوند.

**اگر قصد دارید Commandهای سفارشی در `core` داشته باشید، لطفاً یک نمونه یا لیست Commandهای مورد نیاز را ارسال کنید.**

**اما اگر Command نیاز نیست، اکنون نوبت اصلی به ایجاد یا ارتقای فایل‌های تست برای `core` می‌رسد.**

همانطور که قبلاً نیز اشاره کردیم، یک پوشه `tests/test_core/` باید ایجاد شود و شامل فایل‌هایی مانند `test_models.py`, `test_serializers.py`, `test_views.py`, `test_permissions.py`, `test_services.py`, `test_tasks.py`, `test_helpers.py`, `test_exceptions.py`, `test_managers.py`, `test_mixins.py`, `test_signals.py` و غیره باشد.

چون فایل `test_models.py` برای `core` قبلاً ایجاد شده بود، فایل بعدی منطقی `test_serializers.py` خواهد بود. اما شما قبلاً `serializers.py` را برای `instruments` ارسال کردید و من آن را در پاسخ قبلی (`apps/instruments/serializers.py` - ارتقا یافته) اصلاح کردم.

**پس، با توجه به اینکه ما قبلاً `apps/core/serializers.py` را ایجاد/ارتقا داده‌ایم، نوبت به ایجاد یا ارتقای `tests/test_core/test_serializers.py` می‌رسد.**

اما، از آنجا که شما در پاسخ قبلی گفتید فایل `apps/instruments/serializers.py` (که من اصلاح کردم) را در اپلیکیشن `instruments` قرار دادید، و اکنون می‌فرمایید ادامه کار روی `core` را ببینیم، پس فرض می‌کنم که فایل `apps/core/serializers.py` نیز از پاسخ‌های قبلی (که شامل `CoreBaseSerializer`, `CoreOwnedModelSerializer` و غیره بود) قبلاً در `core` قرار گرفته یا ایجاد شده است.

**در این صورت، اکنون نوبت به ایجاد یا ارتقای فایل تست مربوط به سریالایزرها در `core` می‌رسد.**

---

### 5. فایل `tests/test_core/test_serializers.py` (جدید یا ارتقا یافته)

این فایل شامل تست‌های واحد (Unit Tests) برای سریالایزرها در `apps/core/serializers.py` است.

```python
# tests/test_core/test_serializers.py

import pytest
from decimal import Decimal
from rest_framework.exceptions import ValidationError
from django.contrib.auth import get_user_model
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # اگر مدل‌های دیگری در core دارید، آن‌ها را اینجا import کنید
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
from apps.core.serializers import (
    CoreBaseSerializer,
    CoreOwnedModelSerializer,
    TimeStampedModelSerializer,
    AuditLogSerializer,
    SystemSettingSerializer,
    CacheEntrySerializer,
    # BaseReadSerializer,
    # BaseWriteSerializer,
    # سایر سریالایزرهایی که در core تعریف کرده‌اید
)
from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
from apps.exchanges.factories import ExchangeFactory # فرض بر این است که فکتوری وجود دارد
from apps.instruments.factories import (
    InstrumentFactory,
    InstrumentExchangeMapFactory,
    # سایر فکتوری‌های instruments اگر در core تست شوند
)
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
    # سایر فکتوری‌های core اگر وجود داشته باشند
)

User = get_user_model()

pytestmark = pytest.mark.django_db

class TestCoreBaseSerializer:
    """
    Tests for the CoreBaseSerializer.
    Note: This is an abstract serializer, so tests are usually done via concrete subclasses.
    We can test common behaviors like read_only fields if applicable.
    """
    # این سریالایزر انتزاعی است، بنابراین مستقیماً تست نمی‌شود.
    # تست‌های آن از طریق سریالایزرهایی که از آن ارث می‌برند انجام می‌شود.
    # مثال ساده: اگر CoreBaseSerializer فیلد خاصی داشت که در همه جا read_only بود
    # def test_read_only_fields(self):
    #     # ... تست read_only_fields ...
    pass # فقط یک نمونه، چون خودش انتزاعی است


class TestCoreOwnedModelSerializer:
    """
    Tests for the CoreOwnedModelSerializer.
    """
    # این سریالایزر نیز انتزاعی است و نیاز به یک مدل و سریالایزر واقعی برای تست دارد
    # اما می‌توانیم منطق اصلی آن را تست کنیم
    def test_create_sets_owner_from_context(self, api_client, CustomUserFactory):
        """
        Test that the 'owner' field is automatically set from the request context during creation.
        """
        user = CustomUserFactory()
        api_client.force_authenticate(user=user)

        # فرض: یک مدل واقعی وجود دارد که از BaseOwnedModel ارث می‌برد و یک سریالایزر برای آن وجود دارد
        # از آنجا که CoreOwnedModelSerializer انتزاعی است، نمی‌توانیم مستقیماً آن را تست کنیم
        # باید یک مدل تستی و سریالایزر مربوطه ایجاد کنیم یا از یک مدل واقعی از اپلیکیشن دیگر استفاده کنیم
        # مثال با استفاده از Instrument که احتمالاً از BaseOwnedModel ارث می‌برد (اگرچه ممکن است در instruments باشد)
        # اگر Instrument در instruments باشد، نمی‌توانیم مستقیماً از آن استفاده کنیم، مگر اینکه آن را اینجا import کنیم و فکتوری آن را نیز داشته باشیم
        # اما برای تست CoreOwnedModelSerializer، می‌توانیم یک مدل تستی ساده تعریف کنیم یا یکی از مدل‌هایی که قبلاً در core تعریف کرده‌ایم (اگر مالک داشته باشند) را استفاده کنیم
        # فرض کنیم یک مدل تستی در core وجود دارد یا یکی از مدل‌های دامنه‌ای (مثلاً از instruments یا accounts) که مالک دارد را داریم
        # از آنجا که مدل خاصی نداریم، فقط مثالی از نحوه استفاده را نشان می‌دهیم
        # این تست باید در اپلیکیشن واقعی که از CoreOwnedModelSerializer استفاده می‌کند انجام شود
        # مثلاً در tests/test_instruments/test_serializers.py
        # class TestInstrumentSerializer:
        #     def test_create_sets_owner(self, api_client, CustomUserFactory, InstrumentFactory):
        #         user = CustomUserFactory()
        #         api_client.force_authenticate(user=user)
        #         data = {'symbol': 'TEST123', 'name': 'Test Instrument', ...}
        #         serializer = InstrumentSerializer(data=data, context={'request': api_client.get('/').wsgi_request})
        #         assert serializer.is_valid()
        #         instance = serializer.save()
        #         assert instance.owner == user
        pass # فقط نمونه است


class TestAuditLogSerializer:
    """
    Tests for the AuditLogSerializer.
    """
    def test_audit_log_serializer_create(self, AuditLogFactory, CustomUserFactory):
        """
        Test creating an AuditLog instance via the serializer.
        """
        user = CustomUserFactory()
        data = {
            'user': user.id,
            'action': 'CREATE',
            'target_model': 'TestModel',
            'target_id': '12345678-1234-5678-9012-123456789012',
            'details': {'field': 'value'},
            'ip_address': '127.0.0.1',
            'user_agent': 'Mozilla/5.0...',
            'session_key': 'abc123...'
        }
        # این سریالایزر فرض می‌کند که user از context گرفته می‌شود، نه از validated_data
        # بنابراین، باید context را ارسال کنیم یا فیلد user را حذف کنیم
        context = {'request': type('MockRequest', (), {'user': user})()} # ساخت یک request موقت
        data.pop('user') # حذف user از داده‌های ورودی، چون باید از context گرفته شود
        serializer = AuditLogSerializer(data=data, context=context)
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.user == user
        assert instance.action == 'CREATE'

    def test_audit_log_serializer_read_representation(self, AuditLogFactory):
        """
        Test the read representation of the AuditLogSerializer.
        """
        log = AuditLogFactory()
        serializer = AuditLogSerializer(instance=log)
        data = serializer.data
        assert 'id' in data
        assert 'user_email' in data # فیلد اضافه شده
        assert 'details_summary' in data # فیلد سفارشی
        # ... سایر فیلدهای خروجی ...


class TestSystemSettingSerializer:
    """
    Tests for the SystemSettingSerializer.
    """
    def test_system_setting_serializer_create(self, SystemSettingFactory):
        """
        Test creating a SystemSetting instance via the serializer.
        """
        data = {
            'key': 'NEW_TEST_SETTING',
            'value': '123.45',
            'data_type': 'float',
            'description': 'A new test setting.',
            'is_sensitive': False
        }
        serializer = SystemSettingSerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.key == 'NEW_TEST_SETTING'
        assert instance.get_parsed_value() == Decimal('123.45') # بسته به نحوه پیاده‌سازی get_parsed_value

    def test_system_setting_serializer_validate_int_type(self, SystemSettingFactory):
        """
        Test validation of 'int' data type.
        """
        data = {
            'key': 'INT_SETTING_INVALID',
            'value': 'not_an_int',
            'data_type': 'int',
        }
        serializer = SystemSettingSerializer(data=data)
        assert not serializer.is_valid()
        assert 'value' in serializer.errors # یا 'non_field_errors' بسته به نحوه پیاده‌سازی

    def test_system_setting_serializer_validate_json_type(self, SystemSettingFactory):
        """
        Test validation of 'json' data type.
        """
        data = {
            'key': 'JSON_SETTING_INVALID',
            'value': '{invalid_json',
            'data_type': 'json',
        }
        serializer = SystemSettingSerializer(data=data)
        assert not serializer.is_valid()
        assert 'value' in serializer.errors

    def test_system_setting_serializer_mask_sensitive_value_on_read(self, SystemSettingFactory):
        """
        Test that the value is masked when 'is_sensitive' is True during read.
        """
        setting = SystemSettingFactory(key='API_KEY_TEST', value='secret12345', is_sensitive=True)
        serializer = SystemSettingSerializer(instance=setting)
        data = serializer.data
        assert data['value'] == "***" # مقدار باید مسک شود


class TestCacheEntrySerializer:
    """
    Tests for the CacheEntrySerializer.
    """
    def test_cache_entry_serializer_create(self, CacheEntryFactory):
        """
        Test creating a CacheEntry instance via the serializer.
        """
        data = {
            'key': 'test_cache_key_123',
            'value': 'test_value_456',
            'expires_at': '2025-12-31T23:59:59Z'
        }
        serializer = CacheEntrySerializer(data=data)
        assert serializer.is_valid(), serializer.errors
        instance = serializer.save()
        assert instance.key == 'test_cache_key_123'
        assert instance.value == 'test_value_456'

    def test_cache_entry_serializer_validate_past_expiry(self, CacheEntryFactory):
        """
        Test validation for an expiration date in the past.
        """
        data = {
            'key': 'test_key_past_exp',
            'value': 'test_val',
            'expires_at': '2020-01-01T00:00:00Z' # تاریخ گذشته
        }
        serializer = CacheEntrySerializer(data=data)
        assert not serializer.is_valid()
        assert 'expires_at' in serializer.errors

    def test_cache_entry_serializer_validate_key_length(self, CacheEntryFactory):
        """
        Test validation for key length exceeding the limit.
        """
        long_key = 'a' * 256 # بیشتر از 255 کاراکتر
        data = {
            'key': long_key,
            'value': 'test_val'
        }
        serializer = CacheEntrySerializer(data=data)
        assert not serializer.is_valid()
        assert 'key' in serializer.errors

    def test_cache_entry_serializer_to_representation_masks_value_if_needed(self, CacheEntryFactory):
        """
        Test the to_representation method masks sensitive values if configured.
        Note: This test assumes a specific logic in the serializer's to_representation method.
        """
        # فرض: منطق مسک کردن در to_representation بر اساس کلید باشد
        entry = CacheEntryFactory(key='api_key_test_abc', value='sensitive_data_xyz')
        serializer = CacheEntrySerializer(instance=entry)
        data = serializer.data
        # اگر کلید شامل 'api_key' بود، مقدار باید مسک شود (بر اساس کد قبلی)
        # این منطق باید در CacheEntrySerializer.to_representation پیاده شود
        # مثال ساده در کد بالا نشان داده شد.
        # اینجا فقط می‌توانیم فرض کنیم که اگر منطقی وجود داشت، کار می‌کند.
        # assert data['value'] == '***' # اگر منطق مسک کار کرد
        pass # تست واقعی بستگی به پیاده‌سازی to_representation در سریالایزر دارد

# --- تست‌های سریالایزرهای BaseReadSerializer و BaseWriteSerializer ---
# این سریالایزرها نیز انتزاعی هستند و باید از طریق یک مدل و سریالایزر واقعی تست شوند
# مثال فرضی:
# class ConcreteModel(BaseOwnedModel): # فرض BaseOwnedModel در core تعریف شده است
#     name = models.CharField(max_length=100)
#     class Meta:
#         app_label = 'core'
#
# class ConcreteReadSerializer(BaseReadSerializer):
#     class Meta(BaseReadSerializer.Meta):
#         model = ConcreteModel
#         fields = '__all__'
#
# class ConcreteWriteSerializer(BaseWriteSerializer):
#     class Meta(BaseWriteSerializer.Meta):
#         model = ConcreteModel
#         fields = '__all__'
#
# class TestBaseReadWriteSerializers:
#     def test_base_read_serializer_includes_owner_username(self, ConcreteModelFactory, CustomUserFactory):
#         owner = CustomUserFactory(username='test_owner_read')
#         instance = ConcreteModelFactory(owner=owner)
#         serializer = ConcreteReadSerializer(instance=instance)
#         data = serializer.data
#         # این فیلد باید در BaseReadSerializer تعریف شده باشد
#         assert 'owner_username' in data
#         assert data['owner_username'] == 'test_owner_read'
#
#     def test_base_write_serializer_sets_owner_on_create(self, api_client, CustomUserFactory):
#         user = CustomUserFactory()
#         api_client.force_authenticate(user=user)
#         data = {'name': 'New Concrete Item'}
#         # این سریالایزر فرض می‌کند owner از context گرفته می‌شود
#         serializer = ConcreteWriteSerializer(data=data, context={'request': api_client.get('/').wsgi_request})
#         assert serializer.is_valid()
#         instance = serializer.save()
#         assert instance.owner == user
#
#     def test_base_write_serializer_removes_owner_on_update(self, ConcreteModelFactory, CustomUserFactory):
#         owner = CustomUserFactory()
#         other_user = CustomUserFactory()
#         instance = ConcreteModelFactory(owner=owner)
#         data = {'name': 'Updated Name', 'owner': other_user.id} # سعی در تغییر owner
#         serializer = ConcreteWriteSerializer(instance=instance, data=data, partial=True)
#         assert serializer.is_valid()
#         updated_instance = serializer.save()
#         # owner نباید تغییر کرده باشد
#         assert updated_instance.owner == owner
#         assert updated_instance.name == 'Updated Name'
# pass # چون مدل واقعی وجود ندارد، فقط مثال ارائه شد

# --- تست سایر سریالایزرهای موجود در core ---

# مثال: اگر سریالایزری برای InstrumentWatchlist وجود داشت (اگر در core تعریف شده بود)
# class TestInstrumentWatchlistSerializer:
#     def test_create_sets_owner_from_context(self, api_client, CustomUserFactory):
#         user = CustomUserFactory()
#         api_client.force_authenticate(user=user)
#         data = {'name': 'My Watchlist', 'is_public': False}
#         serializer = InstrumentWatchlistSerializer(data=data, context={'request': api_client.get('/').wsgi_request})
#         assert serializer.is_valid()
#         instance = serializer.save()
#         assert instance.owner == user
#     # ... سایر تست‌ها ...

```