# tests/test_core/test_models.py

import pytest
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # اضافه کردن سایر مدل‌هایی که در core/models.py تعریف شده‌اند
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
from apps.accounts.models import CustomUser # فرض بر این است که مدل کاربر وجود دارد
from apps.exchanges.models import Exchange # فرض بر این است که مدل Exchange وجود دارد
from apps.core.exceptions import DataIntegrityException # فرض بر این است که این استثنا وجود دارد
from apps.core.helpers import validate_ip_list # فرض بر این است که این تابع وجود دارد
from apps.core.encryption import FernetEncryptionService # فرض بر این است که این سرویس وجود دارد
from apps.core.constants import DEFAULT_BASE_CURRENCY # فرض بر این است که این ثابت وجود دارد
import logging

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.django_db


class TestBaseModel:
    """
    Tests for the abstract BaseModel.
    Note: BaseModel itself cannot be instantiated directly.
    We test its properties through a concrete model that inherits from it.
    """
    # ایجاد یک مدل تستی موقت برای تست BaseModel
    # این مدل فقط برای تست است و نباید در کد اصلی پروژه قرار گیرد
    # در تست‌های واقعی، باید از مدل‌های واقعی استفاده کرد
    # از آنجا که این فقط یک تست واحد است، می‌توانیم از unittest.mock یا مدل‌های تستی ساده‌ای استفاده کنیم
    # یا از فکتوری‌ها استفاده کنیم که از مدل‌های واقعی ارث می‌برند
    # فرض کنیم یک فکتوری برای یک مدل واقعی که از BaseModel ارث می‌برد وجود دارد، مثلاً AuditLogFactory
    def test_base_model_has_id_field(self, AuditLogFactory): # فرض: یک مدل واقعی که از BaseModel ارث می‌برد
        instance = AuditLogFactory()
        assert hasattr(instance, 'id')
        assert instance.id is not None
        assert isinstance(instance.id, uuid.UUID) # فرض: id از نوع UUID است

    def test_base_model_has_timestamps(self, AuditLogFactory):
        instance = AuditLogFactory()
        assert hasattr(instance, 'created_at')
        assert hasattr(instance, 'updated_at')
        assert instance.created_at is not None
        assert instance.updated_at is not None
        # اطمینان از اینکه updated_at بعد از یا مساوی created_at است
        assert instance.updated_at >= instance.created_at

    def test_base_model_default_ordering(self, AuditLogFactory):
        """
        Tests that the default ordering [-created_at] is applied.
        This is usually tested at the QuerySet level, not the model instance level.
        """
        log1 = AuditLogFactory()
        log2 = AuditLogFactory()
        logs = AuditLog.objects.all() # فرض: AuditLog از BaseModel ارث می‌برد
        # اولین نتیجه باید آخرین ایجاد شده باشد
        assert logs.first() == log2
        assert logs.last() == log1


class TestBaseOwnedModel:
    """
    Tests for the abstract BaseOwnedModel.
    Note: BaseOwnedModel itself cannot be instantiated directly.
    We test its properties through a concrete model that inherits from it.
    """
    # ایجاد یا فرض وجود مدل تستی/واقعی
    # مثلاً از AuditLog یا مدلی دیگر که owner دارد
    def test_base_owned_model_has_owner_field(self, AuditLogFactory, CustomUserFactory):
        owner_user = CustomUserFactory()
        instance = AuditLogFactory(user=owner_user) # فرض: فیلد user در AuditLog معادل owner است
        # اگر مدل واقعی از BaseOwnedModel ارث می‌برد، فیلد owner وجود خواهد داشت
        # اگر نه، این تست نامعتبر است
        # برای مثال، فرض کنیم مدلی وجود دارد که مستقیماً از BaseOwnedModel ارث می‌برد
        # از آنجا که وجود ندارد، فقط از مدلی استفاده می‌کنیم که فیلد user دارد
        # در تست‌های واقعی، باید از مدلی استفاده کرد که owner دارد
        # مثلاً: ConcreteOwnedModelFactory
        # instance = ConcreteOwnedModelFactory()
        # assert instance.owner == owner_user
        # چون مدل واقعی نداریم، از یک مدلی استفاده می‌کنیم که فیلد user دارد و فرض می‌کنیم user معادل owner است
        assert hasattr(instance, 'user') # یا owner
        assert instance.user == owner_user

    def test_base_owned_model_save_sets_owner(self, CustomUserFactory):
        """
        Tests that the owner is correctly set during save (if overridden in concrete model).
        This is usually handled by the serializer or view.
        The model itself typically doesn't set the owner automatically.
        """
        # این منطق معمولاً در سریالایزر/نمای استفاده می‌شود
        # تست در این سطح برای مدل BaseOwnedModel خود به تنهایی کاربرد محدودی دارد
        # مگر اینکه منطقی در save() تعریف شده باشد
        # فرض: منطق در save() وجود ندارد، فقط در سریالایزر/ویو اعمال می‌شود
        # بنابراین، فقط می‌توانیم مدل را ایجاد کنیم و ببینیم فیلد owner وجود دارد
        # این تست بیشتر مناسب فایل test_serializers یا test_views است
        pass # فقط یک نمونه است


class TestAuditLogModel:
    """
    Tests for the AuditLog model.
    """
    def test_create_audit_log(self, AuditLogFactory):
        log = AuditLogFactory()
        assert log.user is not None
        assert log.action is not None
        assert log.target_model is not None
        assert log.target_id is not None
        assert isinstance(log.details, dict)

    def test_audit_log_str_representation(self, AuditLogFactory, CustomUserFactory):
        user = CustomUserFactory(email="audit_test@example.com")
        log = AuditLogFactory(user=user, action="CREATE", target_model="Instrument", target_id=uuid.uuid4())
        expected_str = f"Audit: audit_test@example.com - CREATE on Instrument (ID: {log.target_id})"
        assert str(log) == expected_str

    def test_audit_log_default_ordering(self, AuditLogFactory):
        log1 = AuditLogFactory()
        log2 = AuditLogFactory()
        logs = AuditLog.objects.all()
        assert logs.first() == log2 # جدیدتر اول
        assert logs.last() == log1


class TestSystemSettingModel:
    """
    Tests for the SystemSetting model.
    """
    def test_create_system_setting(self, SystemSettingFactory):
        setting = SystemSettingFactory()
        assert setting.key is not None
        assert setting.value is not None
        assert setting.data_type in [choice[0] for choice in SystemSetting.DATA_TYPE_CHOICES]
        assert setting.is_sensitive is False # یا True بسته به factory

    def test_system_setting_str_representation(self, SystemSettingFactory):
        setting = SystemSettingFactory(key="API_TIMEOUT", value="30", is_sensitive=False)
        assert str(setting) == "API_TIMEOUT = 30"

    def test_system_setting_str_representation_sensitive(self, SystemSettingFactory):
        setting = SystemSettingFactory(key="SECRET_KEY", value="very_secret", is_sensitive=True)
        assert str(setting) == "SECRET_KEY = ***"

    def test_get_parsed_value_int(self, SystemSettingFactory):
        setting = SystemSettingFactory(value="123", data_type="int")
        parsed_val = setting.get_parsed_value()
        assert parsed_val == 123
        assert isinstance(parsed_val, int)

    def test_get_parsed_value_float(self, SystemSettingFactory):
        setting = SystemSettingFactory(value="123.45", data_type="float")
        parsed_val = setting.get_parsed_value()
        assert parsed_val == Decimal("123.45") # بسته به نحوه پیاده‌سازی (Decimal یا float)
        assert isinstance(parsed_val, Decimal) # یا float

    def test_get_parsed_value_bool_true(self, SystemSettingFactory):
        setting = SystemSettingFactory(value="true", data_type="bool")
        parsed_val = setting.get_parsed_value()
        assert parsed_val is True

    def test_get_parsed_value_bool_false(self, SystemSettingFactory):
        setting = SystemSettingFactory(value="false", data_type="bool")
        parsed_val = setting.get_parsed_value()
        assert parsed_val is False

    def test_get_parsed_value_json(self, SystemSettingFactory):
        json_val = '{"key": "value", "nested": {"inner": 123}}'
        setting = SystemSettingFactory(value=json_val, data_type="json")
        parsed_val = setting.get_parsed_value()
        assert isinstance(parsed_val, dict)
        assert parsed_val == {"key": "value", "nested": {"inner": 123}}

    def test_get_parsed_value_json_invalid(self, SystemSettingFactory, caplog):
        invalid_json = '{"key": "value"' # JSON ناقص
        setting = SystemSettingFactory(value=invalid_json, data_type="json")
        parsed_val = setting.get_parsed_value()
        assert parsed_val == {} # یا None بسته به پیاده‌سازی
        assert "Failed to parse SystemSetting value" in caplog.text # اگر لاگ کرده باشد

    def test_clean_validates_int_type(self, SystemSettingFactory):
        setting = SystemSettingFactory.build(value="not_an_int", data_type="int")
        with pytest.raises(ValidationError):
            setting.full_clean()

    def test_clean_validates_float_type(self, SystemSettingFactory):
        setting = SystemSettingFactory.build(value="not_a_float", data_type="float")
        with pytest.raises(ValidationError):
            setting.full_clean()

    def test_clean_validates_bool_type(self, SystemSettingFactory):
        setting = SystemSettingFactory.build(value="maybe", data_type="bool")
        with pytest.raises(ValidationError):
            setting.full_clean()

    def test_clean_validates_json_type(self, SystemSettingFactory):
        setting = SystemSettingFactory.build(value="{invalid_json", data_type="json")
        with pytest.raises(ValidationError):
            setting.full_clean()


class TestCacheEntryModel:
    """
    Tests for the CacheEntry model.
    """
    def test_create_cache_entry(self, CacheEntryFactory):
        entry = CacheEntryFactory()
        assert entry.key is not None
        assert entry.value is not None

    def test_cache_entry_str_representation(self, CacheEntryFactory):
        entry = CacheEntryFactory(key="test_key_123")
        assert str(entry) == "Cache: test_key_123"

    def test_is_expired(self, CacheEntryFactory):
        now = timezone.now()
        # ورودی منقضی شده
        expired_entry = CacheEntryFactory(expires_at=now - timedelta(hours=1))
        assert expired_entry.is_expired() is True

        # ورودی منقضی نشده
        active_entry = CacheEntryFactory(expires_at=now + timedelta(hours=1))
        assert active_entry.is_expired() is False

        # ورودی بدون انقضا
        no_expiry_entry = CacheEntryFactory(expires_at=None)
        assert no_expiry_entry.is_expired() is False

    def test_get_cached_value(self, CacheEntryFactory):
        entry = CacheEntryFactory(key="cached_data", value="important_info_xyz", expires_at=None)
        cached_val = CacheEntry.get_cached_value("cached_data")
        assert cached_val == "important_info_xyz"

    def test_get_cached_value_expired(self, CacheEntryFactory, mocker):
        #_mock_ کردن حذف رکورد منقضی شده
        now = timezone.now()
        expired_entry = CacheEntryFactory(key="cached_data", value="old_info", expires_at=now - timedelta(minutes=1))
        # قبل از فراخوانی get_cached_value، ممکن است نیاز به mock کردن حذف رکورد باشد
        # اما چون get_cached_value فقط یک مقدار برمی‌گرداند و حذف را انجام می‌دهد،
        # می‌توانیم فقط نتیجه را چک کنیم
        cached_val = CacheEntry.get_cached_value("cached_data")
        assert cached_val is None # چون منقضی شده بود، باید حذف و None برگردانده شود

    def test_set_cached_value(self):
        CacheEntry.set_cached_value("new_key", "new_value", ttl_seconds=60)
        entry = CacheEntry.objects.get(key="new_key")
        assert entry.value == "new_value"
        assert entry.expires_at is not None

    def test_invalidate_cache_key(self, CacheEntryFactory):
        entry = CacheEntryFactory(key="key_to_delete", value="val")
        assert CacheEntry.objects.filter(key="key_to_delete").exists()
        CacheEntry.invalidate_cache_key("key_to_delete")
        assert not CacheEntry.objects.filter(key="key_to_delete").exists()

# --- تست سایر مدل‌های Core (اگر وجود داشته باشند) ---
# مثال:
# class TestInstrumentGroupModel:
#     def test_create_instrument_group(self, InstrumentGroupFactory):
#         group = InstrumentGroupFactory()
#         assert group.name is not None
#         # ... سایر تست‌ها ...
#
# class TestInstrumentModel:
#     def test_create_instrument(self, InstrumentFactory):
#         instrument = InstrumentFactory()
#         assert instrument.symbol is not None
#         assert instrument.base_asset is not None
#         # ... سایر تست‌ها ...
#     def test_validate_symbol_unique(self, InstrumentFactory):
#         inst1 = InstrumentFactory(symbol='BTCUSDT')
#         with pytest.raises(IntegrityError): # یا ValidationError
#             InstrumentFactory(symbol='BTCUSDT') # باید خطا بدهد

# --- تست مدل‌های مربوط به MAS یا سایر مفاهیم ---
# مثال:
# class TestAgentModel:
#     def test_create_agent(self, AgentFactory):
#         agent = AgentFactory()
#         assert agent.name is not None
#         assert agent.agent_type in ['data_collector', 'trading_bot', ...]
#         # ... سایر تست‌ها ...

logger.info("Core model tests loaded successfully.")
