# apps/core/management/commands/setup_system_defaults.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import SystemSetting, InstrumentGroup, InstrumentCategory
from apps.core.services import CoreService
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Sets up default system settings, instrument groups, and categories.'

    def add_arguments(self, parser):
        # parser.add_argument('--force', action='store_true', help='Force overwrite existing defaults.')
        pass

    def handle(self, *args, **options):
        self.stdout.write("Setting up system defaults...")

        # --- ایجاد/بروزرسانی تنظیمات سیستم ---
        defaults = {
            'GLOBAL_RATE_LIMIT_PER_MINUTE': 1000,
            'DEFAULT_MARKET_DATA_BACKEND': 'TIMESCALE',
            'ENABLE_REALTIME_SYNC': True,
            'ENABLE_HISTORICAL_SYNC': True,
            'SYNC_BATCH_SIZE': 1000,
            'DEFAULT_RISK_TOLERANCE': 'medium',
            'MAX_OPEN_ORDERS_PER_INSTRUMENT': 10,
            'MAX_API_KEYS_PER_USER': 5,
            'MAX_WATCHLISTS_PER_USER': 10,
        }

        for key, value in defaults.items():
            setting, created = SystemSetting.objects.update_or_create(
                key=key,
                defaults={
                    'value': str(value), # ذخیره به صورت رشته
                    'data_type': type(value).__name__.lower(), # 'int', 'bool', 'str', 'float'
                    'description': f'Default system setting for {key}',
                    'is_sensitive': False,
                    'is_active': True,
                }
            )
            action = 'Created' if created else 'Updated'
            self.stdout.write(f"  {action} SystemSetting: {key} = {value}")

        # --- ایجاد گروه‌های نماد پیش‌فرض ---
        default_groups = [
            {'name': 'Cryptocurrency', 'description': 'Digital currencies like Bitcoin, Ethereum.', 'supports_leverage': True, 'supports_shorting': True},
            {'name': 'Stock', 'description': 'Equity shares of companies.', 'supports_leverage': False, 'supports_shorting': True},
            {'name': 'Forex', 'description': 'Foreign exchange market pairs.', 'supports_leverage': True, 'supports_shorting': True},
            {'name': 'Commodity', 'description': 'Physical goods like Gold, Oil.', 'supports_leverage': True, 'supports_shorting': True},
            {'name': 'Index', 'description': 'Financial market indices.', 'supports_leverage': True, 'supports_shorting': True},
        ]
        for group_data in default_groups:
            group, created = InstrumentGroup.objects.get_or_create(
                name=group_data['name'],
                defaults={
                    'description': group_data['description'],
                    'supports_leverage': group_data['supports_leverage'],
                    'supports_shorting': group_data['supports_shorting'],
                }
            )
            action = 'Created' if created else 'Found'
            self.stdout.write(f"  {action} Instrument Group: {group.name}")

        # --- ایجاد دسته‌های نماد پیش‌فرض ---
        default_categories = [
            {'name': 'SPOT', 'description': 'Direct trading of the asset.', 'supports_leverage': False, 'supports_shorting': False},
            {'name': 'FUTURES', 'description': 'Futures contracts.', 'supports_leverage': True, 'supports_shorting': True},
            {'name': 'PERPETUAL', 'description': 'Perpetual futures contracts.', 'supports_leverage': True, 'supports_shorting': True},
            {'name': 'OPTION', 'description': 'Option contracts.', 'supports_leverage': True, 'supports_shorting': True},
        ]
        for cat_data in default_categories:
            cat, created = InstrumentCategory.objects.get_or_create(
                name=cat_data['name'],
                defaults={
                    'description': cat_data['description'],
                    'supports_leverage': cat_data['supports_leverage'],
                    'supports_shorting': cat_data['supports_shorting'],
                }
            )
            action = 'Created' if created else 'Found'
            self.stdout.write(f"  {action} Instrument Category: {cat.name}")

        # --- سایر موارد ---
        # مثلاً ایجاد یک کاربر ادمین پیش‌فرض (اگر وجود نداشت)
        # from django.contrib.auth import get_user_model
        # User = get_user_model()
        # admin_user, created = User.objects.get_or_create(
        #     email='admin@example.com',
        #     defaults={'is_staff': True, 'is_superuser': True, 'username': 'admin'}
        # )
        # if created:
        #     admin_user.set_password('default_admin_password') # باید از طریق متغیر محیطی یا ورودی گرفته شود
        #     admin_user.save()
        #     self.stdout.write(f"  Created default admin user: {admin_user.email}")

        self.stdout.write(
            self.style.SUCCESS("System defaults setup completed successfully.")
        )
