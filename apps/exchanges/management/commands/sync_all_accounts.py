# apps/exchanges/management/commands/sync_all_accounts.py

from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.exchanges.models import ExchangeAccount
from apps.exchanges.tasks import sync_exchange_account_task # فرض بر این است که این تاسک وجود دارد
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Syncs all active exchange accounts with their respective exchanges.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if last sync was recent.',
        )
        parser.add_argument(
            '--exchange',
            type=str,
            help='Sync accounts for a specific exchange (e.g., Binance).',
        )

    def handle(self, *args, **options):
        force_sync = options['force']
        exchange_filter = options['exchange']

        queryset = ExchangeAccount.objects.filter(is_active=True)
        if exchange_filter:
            queryset = queryset.filter(exchange__name__iexact=exchange_filter)

        if not force_sync:
            # فقط حساب‌هایی که از مدتی پیش همگام نشده‌اند
            cutoff_time = timezone.now() - timezone.timedelta(minutes=60) # 1 hour
            queryset = queryset.filter(
                models.Q(last_sync_at__isnull=True) | # حساب‌هایی که هیچ‌وقت همگام نشده‌اند
                models.Q(last_sync_at__lt=cutoff_time) # یا زمان آخرین همگام‌سازی بیش از 1 ساعت قبل است
            )

        total_to_sync = queryset.count()
        self.stdout.write(f"Found {total_to_sync} accounts to sync.")

        for account in queryset:
            self.stdout.write(f"Triggering sync for account {account.label} on {account.exchange.name}...")
            # استفاده از تاسک Celery
            sync_exchange_account_task.delay(account.id)
            # یا اگر می‌خواهید به صورت همگام اجرا شود (کندتر، اما ممکن است برای تست مفید باشد)
            # try:
            #     from apps.exchanges.services import ExchangeService
            #     service = ExchangeService()
            #     service.sync_exchange_account(account)
            #     self.stdout.write(self.style.SUCCESS(f"Synced account {account.label} on {account.exchange.name}"))
            # except Exception as e:
            #     self.stdout.write(self.style.ERROR(f"Failed to sync account {account.label}: {e}"))

        self.stdout.write(
            self.style.SUCCESS(f"Successfully triggered sync for {total_to_sync} accounts.")
        )
