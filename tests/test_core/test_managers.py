
# tests/test_core/test_managers.py

import pytest
from django.utils import timezone
from decimal import Decimal
from apps.core.models import (
    BaseModel,
    BaseOwnedModel,
    TimeStampedModel,
    AuditLog,
    SystemSetting,
    CacheEntry,
    # سایر مدل‌هایی که منیجر دارند
    # سایر مدل‌های احتمالی core
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
from apps.core.managers import (
    BaseManager,
    BaseOwnedModelManager,
    TimeStampedModelManager,
    AuditLogManager,
    SystemSettingManager,
    CacheEntryManager,
    # سایر منیجرها و QuerySetهای شما
)
from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
from apps.core.factories import (
    AuditLogFactory,
    SystemSettingFactory,
    CacheEntryFactory,
    # سایر فکتوری‌های core
)

pytestmark = pytest.mark.django_db

class TestBaseManager:
    """
    Tests for the BaseManager and its custom QuerySet methods.
    """
    def test_get_queryset_returns_base_queryset(self, AuditLogFactory):
        """
        Test that BaseManager's get_queryset returns an instance of BaseQuerySet.
        This is implicitly tested as other manager methods rely on it.
        """
        # فرض: AuditLog از BaseModel یا یک مدل مشتق از آن (مثل BaseOwnedModel) ارث می‌برد و از BaseManager یا مشتق آن استفاده می‌کند
        audit_log = AuditLogFactory()
        manager = AuditLog.objects # این منیجر مربوطه را برمی‌گرداند (مثلاً AuditLogManager)
        # اگر AuditLogManager از BaseManager ارث ببرد، این تست کار نمی‌کند
        # بنابراین، باید منیجر مدل خاص را تست کنیم، نه BaseManager خالی
        # این تست فقط زمانی معنی دارد که مدلی وجود داشته باشد که مستقیماً از BaseModel ارث ببرد و از BaseManager استفاده کند
        # مثال: یک مدل تستی ساختگی
        # class ConcreteBaseModel(BaseModel):
        #     name = models.CharField(max_length=100)
        #     objects = BaseManager()
        #     class Meta:
        #         app_label = 'core'
        # instance = ConcreteBaseModel.objects.create(name='test')
        # qs = ConcreteBaseModel.objects.get_queryset()
        # assert isinstance(qs, BaseQuerySet) # فرض BaseQuerySet از models.QuerySet ارث می‌برد
        pass # چون BaseManager انتزاعی است و مستقیماً استفاده نمی‌شود، فقط می‌توان از آن ارث برد


class TestBaseOwnedModelManager:
    """
    Tests for the BaseOwnedModelManager and its custom QuerySet methods.
    """
    def test_get_queryset_filters_by_owner(self, AuditLogFactory, CustomUserFactory):
        """
        Test that BaseOwnedModelManager's get_queryset filters by the current user's ownership (when used in a view context).
        Note: This manager's queryset should be used in conjunction with a view that injects the user.
        Direct use of manager here will not filter by owner.
        """
        # این منیجر نیاز به کاربر فعلی دارد که معمولاً از طریق نما (View) یا سرویس فراهم می‌شود
        # بنابراین، تست مستقیم get_queryset از این منیجر در اینجا معنی ندارد
        # تست این فیلتر باید در تست نماها (Views) انجام شود
        # اما می‌توانیم متدهایی که در QuerySet آن تعریف شده را تست کنیم
        owner_user = CustomUserFactory()
        other_user = CustomUserFactory()

        owned_log = AuditLogFactory(user=owner_user) # فرض: user معادل owner است
        other_log = AuditLogFactory(user=other_user)

        # استفاده از متد خاص QuerySet (مثلاً owned_by)
        user_logs = AuditLog.objects.owned_by(owner_user)

        assert owned_log in user_logs
        assert other_log not in user_logs
        assert user_logs.count() == 1

    def test_owned_active_filter(self, AuditLogFactory, CustomUserFactory):
        """
        Test the owned_active filter method on the BaseOwnedModelQuerySet.
        """
        owner_user = CustomUserFactory()
        active_log = AuditLogFactory(user=owner_user, is_active=True)
        inactive_log = AuditLogFactory(user=owner_user, is_active=False)
        other_inactive_log = AuditLogFactory(user=CustomUserFactory(), is_active=False)

        owned_active_logs = AuditLog.objects.owned_active(owner_user)

        assert active_log in owned_active_logs
        assert inactive_log not in owned_active_logs
        assert other_inactive_log not in owned_active_logs
        assert owned_active_logs.count() == 1


class TestAuditLogManager:
    """
    Tests for the AuditLogManager and its custom methods.
    """
    def test_get_by_user(self, AuditLogFactory, CustomUserFactory):
        """
        Test the get_by_user manager method.
        """
        user = CustomUserFactory()
        other_user = CustomUserFactory()

        log1 = AuditLogFactory(user=user, action='ACTION_1')
        log2 = AuditLogFactory(user=user, action='ACTION_2')
        log3 = AuditLogFactory(user=other_user, action='ACTION_3')

        user_logs = AuditLog.objects.get_by_user(user)

        assert log1 in user_logs
        assert log2 in user_logs
        assert log3 not in user_logs
        assert user_logs.count() == 2

    def test_get_by_target(self, AuditLogFactory, CustomUserFactory):
        """
        Test the get_by_target manager method.
        """
        user = CustomUserFactory()
        log1 = AuditLogFactory(user=user, target_model='User', target_id=user.id, action='UPDATE_PROFILE')
        log2 = AuditLogFactory(user=user, target_model='Instrument', target_id='12345', action='PLACE_ORDER')

        target_logs = AuditLog.objects.get_by_target('User', user.id)

        assert log1 in target_logs
        assert log2 not in target_logs
        assert target_logs.count() == 1

    def test_get_by_action(self, AuditLogFactory, CustomUserFactory):
        """
        Test the get_by_action manager method.
        """
        user = CustomUserFactory()
        log1 = AuditLogFactory(user=user, action='LOGIN')
        log2 = AuditLogFactory(user=user, action='LOGOUT')
        log3 = AuditLogFactory(user=user, action='LOGIN')

        login_logs = AuditLog.objects.get_by_action('LOGIN')

        assert log1 in login_logs
        assert log3 in login_logs
        assert log2 not in login_logs
        assert login_logs.count() == 2

    def test_get_recent_logs(self, AuditLogFactory, CustomUserFactory):
        """
        Test the get_recent_logs manager method.
        """
        user = CustomUserFactory()
        now = timezone.now()

        recent_log = AuditLogFactory(user=user, created_at=now - timezone.timedelta(minutes=30))
        old_log = AuditLogFactory(user=user, created_at=now - timezone.timedelta(hours=2))

        recent_logs = AuditLog.objects.get_recent_logs(user, hours=1)

        assert recent_log in recent_logs
        assert old_log not in recent_logs
        assert recent_logs.count() == 1


class TestSystemSettingManager:
    """
    Tests for the SystemSettingManager and its custom methods.
    """
    def test_get_cached_value_hits_cache(self, mocker, SystemSettingFactory):
        """
        Test that get_cached_value retrieves from cache if available.
        """
        from django.core.cache import cache
        setting = SystemSettingFactory(key='CACHED_TEST_KEY', value='cached_val', is_active=True)
        cache_key = f"sys_setting_{setting.key.lower()}"

        # ابتدا در کش قرار می‌دهیم
        cache.set(cache_key, 'cached_val_from_cache', timeout=3600)

        # اکنون get_cached_value باید از کش بخواند
        retrieved_val = SystemSetting.objects.get_cached_value('CACHED_TEST_KEY', default='default_val')

        assert retrieved_val == 'cached_val_from_cache'

    def test_get_cached_value_fallbacks_to_db(self, mocker, SystemSettingFactory):
        """
        Test that get_cached_value falls back to database if not in cache.
        """
        from django.core.cache import cache
        setting = SystemSettingFactory(key='DB_FALLBACK_KEY', value='db_val', is_active=True)
        cache_key = f"sys_setting_{setting.key.lower()}"

        # اطمینان از عدم وجود در کش
        cache.delete(cache_key)

        retrieved_val = SystemSetting.objects.get_cached_value('DB_FALLBACK_KEY', default='default_val')

        assert retrieved_val == 'db_val' # از DB گرفته شده است
        # و اکنون در کش نیز باید باشد
        assert cache.get(cache_key) == 'db_val'

    def test_get_cached_value_not_found_returns_default(self, mocker):
        """
        Test that get_cached_value returns default if setting not found in cache or DB.
        """
        from django.core.cache import cache
        cache.delete('sys_setting_non_existent_key')

        retrieved_val = SystemSetting.objects.get_cached_value('NON_EXISTENT_KEY', default='default_returned')

        assert retrieved_val == 'default_returned'

    def test_set_value_creates_or_updates_and_clears_cache(self, mocker):
        """
        Test the set_value manager method creates/updates and clears the cache.
        """
        from django.core.cache import cache
        cache_key = "sys_setting_new_test_key"

        # حذف احتمالی قبلی
        cache.delete(cache_key)
        SystemSetting.objects.filter(key='NEW_TEST_KEY').delete()

        setting = SystemSetting.objects.set_value(
            key='NEW_TEST_KEY',
            value='new_test_val',
            data_type='str',
            description='A new test setting.',
            is_sensitive=False
        )

        assert setting.key == 'NEW_TEST_KEY'
        assert setting.get_parsed_value() == 'new_test_val'
        # کش باید حذف شده باشد (چون بعد از ذخیره، مقدار جدید در کش نیست، تا زمانی که دوباره گرفته شود)
        cached_val_after_set = cache.get(cache_key)
        assert cached_val_after_set is None # چون فقط هنگام گرفتن، در کش قرار می‌گیرد

        # اکنون گرفتن مقدار باید DB را بخواند و مقدار جدید را بدهد و در کش قرار دهد
        retrieved_after_set = SystemSetting.objects.get_cached_value('NEW_TEST_KEY')
        assert retrieved_after_set == 'new_test_val'
        assert cache.get(cache_key) == 'new_test_val'

    def test_get_value_by_key(self, SystemSettingFactory):
        """
        Test the get_value_by_key custom QuerySet method.
        """
        setting = SystemSettingFactory(key='QUERY_TEST_KEY', value='queried_val', is_active=True)

        retrieved_val = SystemSetting.objects.get_value_by_key('QUERY_TEST_KEY')

        assert retrieved_val == 'queried_val'

    def test_get_value_by_key_not_found(self):
        """
        Test the get_value_by_key method returns default if not found.
        """
        retrieved_val = SystemSetting.objects.get_value_by_key('NON_EXISTENT_QUERY_KEY', default='default_query')

        assert retrieved_val == 'default_query'

    def test_get_value_by_key_inactive(self, SystemSettingFactory):
        """
        Test the get_value_by_key method returns default if setting is inactive.
        """
        setting = SystemSettingFactory(key='INACTIVE_QUERY_KEY', value='inactive_val', is_active=False)

        retrieved_val = SystemSetting.objects.get_value_by_key('INACTIVE_QUERY_KEY', default='default_inactive')

        assert retrieved_val == 'default_inactive'


class TestCacheEntryManager:
    """
    Tests for the CacheEntryManager and its custom methods.
    """
    def test_get_from_db_cache(self, CacheEntryFactory):
        """
        Test the get_from_db_cache manager method.
        """
        entry = CacheEntryFactory(key='db_cache_test_key', value='db_cache_val', expires_at=None)
        retrieved_val = CacheEntry.objects.get_from_db_cache('db_cache_test_key')
        assert retrieved_val == 'db_cache_val'

    def test_get_from_db_cache_expired(self, CacheEntryFactory):
        """
        Test the get_from_db_cache method with an expired entry.
        """
        now = timezone.now()
        expired_entry = CacheEntryFactory(
            key='db_cache_expired_key',
            value='old_db_val',
            expires_at=now - timezone.timedelta(seconds=1)
        )
        retrieved_val = CacheEntry.objects.get_from_db_cache('db_cache_expired_key')
        assert retrieved_val is None
        # ورودی باید حذف شده باشد
        assert not CacheEntry.objects.filter(id=expired_entry.id).exists()

    def test_set_in_db_cache(self, mocker):
        """
        Test the set_in_db_cache manager method.
        """
        key = 'new_db_cache_key'
        value = 'new_db_cache_val'
        ttl = 1800

        CacheEntry.objects.set_in_db_cache(key, value, ttl_seconds=ttl)

        saved_entry = CacheEntry.objects.get(key=key)
        assert saved_entry.value == value
        # چک کردن انقضا (تقریبی)
        expected_expiry = timezone.now() + timezone.timedelta(seconds=ttl)
        assert abs((saved_entry.expires_at - expected_expiry).total_seconds()) < 5 # اختلاف کمتر از 5 ثانیه

    def test_get_cached_value_queryset_method(self, CacheEntryFactory):
        """
        Test the get_cached_value custom QuerySet method.
        """
        entry = CacheEntryFactory(key='qs_test_key', value='qs_test_val', expires_at=None)

        retrieved_val = CacheEntry.objects.get_cached_value('qs_test_key')

        assert retrieved_val == 'qs_test_val'

    def test_get_cached_value_queryset_method_expired(self, CacheEntryFactory):
        """
        Test the get_cached_value QuerySet method with an expired entry.
        """
        now = timezone.now()
        expired_entry = CacheEntryFactory(
            key='qs_expired_key',
            value='old_qs_val',
            expires_at=now - timezone.timedelta(seconds=1)
        )

        retrieved_val = CacheEntry.objects.get_cached_value('qs_expired_key')

        assert retrieved_val is None
        assert not CacheEntry.objects.filter(id=expired_entry.id).exists() # حذف شده است


# --- تست منیجرهای مدل‌های دیگر ---
# می‌توانید تست‌هایی برای منیجرهایی که برای سایر مدل‌هایی که در core/models.py تعریف می‌کنید بنویسید
# مثلاً اگر مدل InstrumentWatchlist وجود داشت و منیجر داشت:
# class TestInstrumentWatchlistManager:
#     def test_method(self, InstrumentWatchlistFactory, CustomUserFactory):
#         user = CustomUserFactory()
#         wl = InstrumentWatchlistFactory(owner=user)
#         assert wl in InstrumentWatchlist.objects.for_user(user)

logger.info("Core manager tests loaded successfully.")







# # tests/test_core/test_managers.py
#
# import pytest
# from django.utils import timezone
# from decimal import Decimal
# from apps.core.models import (
#     BaseModel,
#     BaseOwnedModel,
#     TimeStampedModel,
#     AuditLog,
#     SystemSetting,
#     CacheEntry,
#     # سایر مدل‌های احتمالی core
#     # InstrumentGroup,
#     # InstrumentCategory,
#     # Instrument,
#     # InstrumentExchangeMap,
#     # IndicatorGroup,
#     # Indicator,
#     # IndicatorParameter,
#     # IndicatorTemplate,
#     # PriceActionPattern,
#     # SmartMoneyConcept,
#     # AIMetric,
#     # InstrumentWatchlist,
# )
# from apps.core.managers import (
#     BaseManager,
#     BaseOwnedModelManager,
#     TimeStampedModelManager,
#     AuditLogManager,
#     SystemSettingManager,
#     CacheEntryManager,
#     # سایر منیجرها و QuerySetهای شما
# )
# from apps.accounts.factories import CustomUserFactory # فرض بر این است که فکتوری وجود دارد
# from apps.core.factories import (
#     AuditLogFactory,
#     SystemSettingFactory,
#     CacheEntryFactory,
#     # سایر فکتوری‌های core
# )
#
# pytestmark = pytest.mark.django_db
#
# class TestBaseManager:
#     """
#     Tests for the BaseManager and its custom QuerySet methods.
#     """
#     def test_get_queryset_returns_base_queryset(self, AuditLogFactory):
#         """
#         Test that BaseManager's get_queryset returns an instance of BaseQuerySet.
#         This is implicitly tested as other manager methods rely on it.
#         """
#         # فرض: AuditLog از BaseModel ارث می‌برد و از BaseManager (یا یک منیجر ارث گرفته از آن) استفاده می‌کند
#         audit_log = AuditLogFactory()
#         manager = AuditLog.objects # این از BaseOwnedManager (که از BaseManager ارث می‌برد) استفاده می‌کند
#         qs = manager.get_queryset()
#         # چون BaseOwnedModelManager از BaseManager ارث می‌برد، و AuditLog از BaseOwnedModel،
#         # منیجر آن BaseOwnedModelManager است که CoreBaseQuerySet را برمی‌گرداند.
#         # بنابراین، متد active در CoreBaseQuerySet قابل استفاده است
#         # اگر CoreBaseQuerySet وجود نداشت، این تست نامعتبر است
#         # اما اگر AuditLog از BaseOwnedModel ارث ببرد، از CoreOwnedModelManager استفاده می‌کند
#         # که CoreOwnedModelQuerySet را برمی‌گرداند و CoreOwnedModelQuerySet از CoreBaseQuerySet ارث می‌برد
#         # بنابراین، active باید کار کند
#         active_logs = qs.active() # این متد از CoreBaseQuerySet است
#         assert audit_log in active_logs
#
#     def test_active_filter(self, AuditLogFactory):
#         """
#         Test the active filter method on the BaseQuerySet.
#         """
#         active_log = AuditLogFactory(is_active=True)
#         inactive_log = AuditLogFactory(is_active=False)
#
#         active_logs = AuditLog.objects.active()
#
#         assert active_log in active_logs
#         assert inactive_log not in active_logs
#         assert active_logs.count() == 1
#
#     def test_inactive_filter(self, AuditLogFactory):
#         """
#         Test the inactive filter method on the BaseQuerySet.
#         """
#         active_log = AuditLogFactory(is_active=True)
#         inactive_log = AuditLogFactory(is_active=False)
#
#         inactive_logs = AuditLog.objects.inactive()
#
#         assert inactive_log in inactive_logs
#         assert active_log not in inactive_logs
#         assert inactive_logs.count() == 1
#
#     def test_created_after_filter(self, AuditLogFactory):
#         """
#         Test the created_after filter method.
#         """
#         now = timezone.now()
#         old_log = AuditLogFactory(created_at=now - timezone.timedelta(hours=2))
#         new_log = AuditLogFactory(created_at=now - timezone.timedelta(hours=1))
#
#         logs_after_old = AuditLog.objects.created_after(now - timezone.timedelta(hours=1.5))
#
#         assert new_log in logs_after_old
#         assert old_log not in logs_after_old
#
#     def test_created_before_filter(self, AuditLogFactory):
#         """
#         Test the created_before filter method.
#         """
#         now = timezone.now()
#         old_log = AuditLogFactory(created_at=now - timezone.timedelta(hours=2))
#         new_log = AuditLogFactory(created_at=now - timezone.timedelta(hours=1))
#
#         logs_before_new = AuditLog.objects.created_before(now - timezone.timedelta(hours=1.5))
#
#         assert old_log in logs_before_new
#         assert new_log not in logs_before_new
#
#     def test_updated_after_filter(self, AuditLogFactory):
#         """
#         Test the updated_after filter method.
#         """
#         now = timezone.now()
#         log = AuditLogFactory()
#         log.updated_at = now - timezone.timedelta(hours=1)
#         log.save(update_fields=['updated_at'])
#
#         old_log = AuditLogFactory(updated_at=now - timezone.timedelta(hours=2))
#
#         logs_after_old = AuditLog.objects.updated_after(now - timezone.timedelta(hours=1.5))
#
#         assert log in logs_after_old
#         assert old_log not in logs_after_old
#
#     def test_updated_before_filter(self, AuditLogFactory):
#         """
#         Test the updated_before filter method.
#         """
#         now = timezone.now()
#         log = AuditLogFactory()
#         log.updated_at = now - timezone.timedelta(hours=2)
#         log.save(update_fields=['updated_at'])
#
#         new_log = AuditLogFactory(updated_at=now - timezone.timedelta(hours=1))
#
#         logs_before_new = AuditLog.objects.updated_before(now - timezone.timedelta(hours=1.5))
#
#         assert log in logs_before_new
#         assert new_log not in logs_before_new
#
#
# class TestBaseOwnedModelManager:
#     """
#     Tests for the BaseOwnedModelManager and its custom QuerySet methods.
#     """
#     def test_owned_by_filter(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the owned_by filter method on the BaseOwnedModelQuerySet.
#         """
#         owner_user = CustomUserFactory()
#         other_user = CustomUserFactory()
#
#         owned_log = AuditLogFactory(user=owner_user) # فرض: user معادل owner است
#         other_log = AuditLogFactory(user=other_user)
#
#         user_logs = AuditLog.objects.owned_by(owner_user)
#
#         assert owned_log in user_logs
#         assert other_log not in user_logs
#         assert user_logs.count() == 1
#
#     def test_not_owned_by_filter(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the not_owned_by filter method.
#         """
#         owner_user = CustomUserFactory()
#         other_user = CustomUserFactory()
#
#         owned_log = AuditLogFactory(user=owner_user)
#         other_log = AuditLogFactory(user=other_user)
#
#         logs_not_by_owner = AuditLog.objects.not_owned_by(owner_user)
#
#         assert other_log in logs_not_by_owner
#         assert owned_log not in logs_not_by_owner
#         assert logs_not_by_owner.count() == 1
#
#     def test_for_user_filter(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the for_user filter method (alias for owned_by).
#         """
#         user = CustomUserFactory()
#         log = AuditLogFactory(user=user)
#         other_log = AuditLogFactory()
#
#         user_logs = AuditLog.objects.for_user(user)
#
#         assert log in user_logs
#         assert other_log not in user_logs
#         assert user_logs.count() == 1
#
#     def test_owned_active_filter(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the owned_active filter method.
#         """
#         user = CustomUserFactory()
#         active_log = AuditLogFactory(user=user, is_active=True)
#         inactive_log = AuditLogFactory(user=user, is_active=False)
#         other_inactive_log = AuditLogFactory(user=CustomUserFactory(), is_active=False)
#
#         owned_active_logs = AuditLog.objects.owned_active(user)
#
#         assert active_log in owned_active_logs
#         assert inactive_log not in owned_active_logs
#         assert other_inactive_log not in owned_active_logs
#         assert owned_active_logs.count() == 1
#
#
# class TestAuditLogManager:
#     """
#     Tests for the AuditLogManager and its custom methods.
#     """
#     def test_get_by_user(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the get_by_user manager method.
#         """
#         user = CustomUserFactory()
#         other_user = CustomUserFactory()
#
#         log1 = AuditLogFactory(user=user, action='ACTION_1')
#         log2 = AuditLogFactory(user=user, action='ACTION_2')
#         log3 = AuditLogFactory(user=other_user, action='ACTION_3')
#
#         user_logs = AuditLog.objects.get_by_user(user)
#
#         assert log1 in user_logs
#         assert log2 in user_logs
#         assert log3 not in user_logs
#         assert user_logs.count() == 2
#
#     def test_get_by_target(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the get_by_target manager method.
#         """
#         user = CustomUserFactory()
#         log1 = AuditLogFactory(user=user, target_model='User', target_id=user.id, action='UPDATE_PROFILE')
#         log2 = AuditLogFactory(user=user, target_model='Instrument', target_id='12345', action='PLACE_ORDER')
#
#         target_logs = AuditLog.objects.get_by_target('User', user.id)
#
#         assert log1 in target_logs
#         assert log2 not in target_logs
#         assert target_logs.count() == 1
#
#     def test_get_by_action(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the get_by_action manager method.
#         """
#         user = CustomUserFactory()
#         log1 = AuditLogFactory(user=user, action='LOGIN')
#         log2 = AuditLogFactory(user=user, action='LOGOUT')
#         log3 = AuditLogFactory(user=user, action='LOGIN')
#
#         login_logs = AuditLog.objects.get_by_action('LOGIN')
#
#         assert log1 in login_logs
#         assert log3 in login_logs
#         assert log2 not in login_logs
#         assert login_logs.count() == 2
#
#     def test_get_recent_logs(self, AuditLogFactory, CustomUserFactory):
#         """
#         Test the get_recent_logs manager method.
#         """
#         user = CustomUserFactory()
#         now = timezone.now()
#         recent_log = AuditLogFactory(user=user, created_at=now - timezone.timedelta(minutes=5))
#         old_log = AuditLogFactory(user=user, created_at=now - timezone.timedelta(hours=2))
#
#         recent_logs = AuditLog.objects.get_recent_logs(user, hours=1)
#
#         assert recent_log in recent_logs
#         assert old_log not in recent_logs
#         assert recent_logs.count() == 1
#
#
# class TestSystemSettingManager:
#     """
#     Tests for the SystemSettingManager and its custom methods.
#     """
#     def test_get_cached_value_hits_cache(self, mocker, SystemSettingFactory):
#         """
#         Test that get_cached_value retrieves from cache if available.
#         """
#         from django.core.cache import cache
#         setting = SystemSettingFactory(key='CACHED_TEST_KEY', value='cached_val', is_active=True)
#         cache_key = f"sys_setting_{setting.key.lower()}"
#
#         # ابتدا در کش قرار می‌دهیم
#         cache.set(cache_key, 'cached_val_from_cache', timeout=3600)
#
#         # اکنون get_cached_value باید از کش بخواند
#         retrieved_val = SystemSetting.objects.get_cached_value('CACHED_TEST_KEY', default='default_val')
#
#         assert retrieved_val == 'cached_val_from_cache'
#
#     def test_get_cached_value_fallbacks_to_db(self, mocker, SystemSettingFactory):
#         """
#         Test that get_cached_value falls back to database if not in cache.
#         """
#         from django.core.cache import cache
#         setting = SystemSettingFactory(key='DB_FALLBACK_KEY', value='db_val', is_active=True)
#         cache_key = f"sys_setting_{setting.key.lower()}"
#
#         # اطمینان از عدم وجود در کش
#         cache.delete(cache_key)
#
#         retrieved_val = SystemSetting.objects.get_cached_value('DB_FALLBACK_KEY', default='default_val')
#
#         assert retrieved_val == 'db_val' # از DB گرفته شده است
#         # و اکنون در کش نیز باید باشد
#         assert cache.get(cache_key) == 'db_val'
#
#     def test_get_cached_value_not_found_returns_default(self, mocker):
#         """
#         Test that get_cached_value returns default if setting not found in cache or DB.
#         """
#         from django.core.cache import cache
#         cache.delete('sys_setting_non_existent_key')
#
#         retrieved_val = SystemSetting.objects.get_cached_value('NON_EXISTENT_KEY', default='default_returned')
#
#         assert retrieved_val == 'default_returned'
#
#     def test_set_value_creates_or_updates_and_clears_cache(self, mocker):
#         """
#         Test the set_value manager method creates/updates and clears the cache.
#         """
#         from django.core.cache import cache
#         cache_key = "sys_setting_new_test_key"
#
#         # حذف احتمالی قبلی
#         cache.delete(cache_key)
#         SystemSetting.objects.filter(key='NEW_TEST_KEY').delete()
#
#         setting = SystemSetting.objects.set_value(
#             key='NEW_TEST_KEY',
#             value='new_test_val',
#             data_type='str',
#             description='A new test setting.',
#             is_sensitive=False
#         )
#
#         assert setting.key == 'NEW_TEST_KEY'
#         assert setting.get_parsed_value() == 'new_test_val'
#         # کش باید حذف شده باشد (چون فقط هنگام گرفتن، در کش قرار می‌گیرد)
#         cached_val_after_set = cache.get(cache_key)
#         assert cached_val_after_set is None
#
#         # اکنون گرفتن مقدار باید DB را بخواند و مقدار جدید را بدهد و در کش قرار دهد
#         retrieved_after_set = SystemSetting.objects.get_cached_value('NEW_TEST_KEY')
#         assert retrieved_after_set == 'new_test_val'
#         assert cache.get(cache_key) == 'new_test_val'
#
#     def test_get_value_by_key(self, SystemSettingFactory):
#         """
#         Test the get_value_by_key custom QuerySet method.
#         """
#         setting = SystemSettingFactory(key='QUERY_TEST_KEY', value='queried_val', is_active=True)
#
#         retrieved_val = SystemSetting.objects.get_value_by_key('QUERY_TEST_KEY')
#
#         assert retrieved_val == 'queried_val'
#
#     def test_get_value_by_key_not_found(self):
#         """
#         Test the get_value_by_key method returns default if not found.
#         """
#         retrieved_val = SystemSetting.objects.get_value_by_key('NON_EXISTENT_QUERY_KEY', default='default_query')
#
#         assert retrieved_val == 'default_query'
#
#     def test_get_value_by_key_inactive(self, SystemSettingFactory):
#         """
#         Test the get_value_by_key method returns default if setting is inactive.
#         """
#         setting = SystemSettingFactory(key='INACTIVE_QUERY_KEY', value='inactive_val', is_active=False)
#
#         retrieved_val = SystemSetting.objects.get_value_by_key('INACTIVE_QUERY_KEY', default='default_inactive')
#
#         assert retrieved_val == 'default_inactive'
#
#
# class TestCacheEntryManager:
#     """
#     Tests for the CacheEntryManager and its custom methods.
#     """
#     def test_get_from_db_cache(self, CacheEntryFactory):
#         """
#         Test the get_from_db_cache manager method.
#         """
#         entry = CacheEntryFactory(key='db_cache_test_key', value='db_cache_val', expires_at=None)
#         retrieved_val = CacheEntry.objects.get_from_db_cache('db_cache_test_key')
#         assert retrieved_val == 'db_cache_val'
#
#     def test_get_from_db_cache_expired(self, CacheEntryFactory):
#         """
#         Test the get_from_db_cache method with an expired entry.
#         """
#         now = timezone.now()
#         expired_entry = CacheEntryFactory(
#             key='db_cache_expired_key',
#             value='old_db_val',
#             expires_at=now - timezone.timedelta(seconds=1)
#         )
#         retrieved_val = CacheEntry.objects.get_from_db_cache('db_cache_expired_key')
#         assert retrieved_val is None
#         # ورودی باید حذف شده باشد
#         assert not CacheEntry.objects.filter(id=expired_entry.id).exists()
#
#     def test_set_in_db_cache(self, mocker):
#         """
#         Test the set_in_db_cache manager method.
#         """
#         key = 'new_db_cache_key'
#         value = 'new_db_cache_val'
#         ttl = 1800
#
#         CacheEntry.objects.set_in_db_cache(key, value, ttl_seconds=ttl)
#
#         saved_entry = CacheEntry.objects.get(key=key)
#         assert saved_entry.value == value
#         # چک کردن انقضا (تقریبی)
#         expected_expiry = timezone.now() + timezone.timedelta(seconds=ttl)
#         assert abs((saved_entry.expires_at - expected_expiry).total_seconds()) < 5 # اختلاف کمتر از 5 ثانیه
#
#     def test_get_cached_value_queryset_method(self, CacheEntryFactory):
#         """
#         Test the get_cached_value custom QuerySet method.
#         """
#         entry = CacheEntryFactory(key='qs_test_key', value='qs_test_val', expires_at=None)
#
#         retrieved_val = CacheEntry.objects.get_cached_value('qs_test_key')
#
#         assert retrieved_val == 'qs_test_val'
#
#     def test_get_cached_value_queryset_method_expired(self, CacheEntryFactory):
#         """
#         Test the get_cached_value QuerySet method with an expired entry.
#         """
#         now = timezone.now()
#         expired_entry = CacheEntryFactory(
#             key='qs_expired_key',
#             value='old_qs_val',
#             expires_at=now - timezone.timedelta(seconds=1)
#         )
#
#         retrieved_val = CacheEntry.objects.get_cached_value('qs_expired_key')
#
#         assert retrieved_val is None
#         assert not CacheEntry.objects.filter(id=expired_entry.id).exists() # حذف شده است
#
#
# # --- تست سایر منیجرها و QuerySetها ---
# # می‌توانید برای سایر منیجرها و QuerySetهایی که در core/managers.py تعریف می‌کنید تست بنویسید
# # مثلاً اگر TimeStampedManager وجود داشت:
# class TestTimeStampedManager:
#     """
#     Tests for the TimeStampedManager and its custom QuerySet methods.
#     """
#     def test_recently_created_filter(self, AuditLogFactory):
#         """
#         Test the recently_created filter method.
#         """
#         now = timezone.now()
#         old_log = AuditLogFactory(created_at=now - timezone.timedelta(hours=25))
#         recent_log = AuditLogFactory(created_at=now - timezone.timedelta(hours=23))
#
#         recent_logs = AuditLog.objects.recently_created(hours=24)
#
#         assert recent_log in recent_logs
#         assert old_log not in recent_logs
#
#     def test_recently_updated_filter(self, AuditLogFactory):
#         """
#         Test the recently_updated filter method.
#         """
#         now = timezone.now()
#         log = AuditLogFactory()
#         log.updated_at = now - timezone.timedelta(hours=1) # بروزرسانی زمان
#         log.save(update_fields=['updated_at'])
#
#         old_log = AuditLogFactory(updated_at=now - timezone.timedelta(hours=25))
#
#         recent_logs = AuditLog.objects.recently_updated(hours=24)
#
#         assert log in recent_logs
#         assert old_log not in recent_logs
#
#     def test_older_than_filter(self, AuditLogFactory):
#         """
#         Test the older_than filter method.
#         """
#         now = timezone.now()
#         old_log = AuditLogFactory(created_at=now - timezone.timedelta(days=31)) # بیشتر از 30 روز
#         recent_log = AuditLogFactory(created_at=now - timezone.timedelta(days=29))
#
#         old_logs = AuditLog.objects.older_than(days=30)
#
#         assert old_log in old_logs
#         assert recent_log not in old_logs
#
#     def test_created_between_dates_filter(self, AuditLogFactory):
#         """
#         Test the created_between_dates filter method.
#         """
#         start_date = timezone.now() - timezone.timedelta(days=10)
#         end_date = timezone.now() - timezone.timedelta(days=5)
#
#         log_in_range = AuditLogFactory(created_at=start_date + timezone.timedelta(days=2))
#         log_before_range = AuditLogFactory(created_at=start_date - timezone.timedelta(days=1))
#         log_after_range = AuditLogFactory(created_at=end_date + timezone.timedelta(days=1))
#
#         logs_in_date_range = AuditLog.objects.created_between_dates(start_date, end_date)
#
#         assert log_in_range in logs_in_date_range
#         assert log_before_range not in logs_in_date_range
#         assert log_after_range not in logs_in_date_range
#
# logger.info("Core manager tests loaded successfully.")
