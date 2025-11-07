from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission
from django.db import models

# 1. مدل کاربر و مدیریت هویت و دسترسی
class User(AbstractUser):
    groups = models.ManyToManyField(
        Group,
        related_name='trading_user_set',
        blank=True,
        help_text=('The groups this user belongs to. A user will get all permissions '
                   'granted to each of their groups.'),
        verbose_name='groups',
        related_query_name='user',
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='trading_user_set',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
        related_query_name='user',
    )



##############################################3
##############################################


class Role(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class UserRole(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role')


# 2. مدل استراتژی‌ها و بخش‌های مرتبط
class Strategy(models.Model):
    PREDEFINED = 'predefined'
    CUSTOM = 'custom'
    STRATEGY_TYPES = [
        (PREDEFINED, 'Predefined'),
        (CUSTOM, 'Custom'),
    ]

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='strategies')
    type = models.CharField(max_length=50, choices=STRATEGY_TYPES)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']
        db_table = 'strategy'

    def __str__(self):
        return self.name


class Indicator(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    parameters_template = models.JSONField(help_text="Default parameters for this indicator")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class StrategyIndicator(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    indicator = models.ForeignKey(Indicator, on_delete=models.CASCADE)
    parameters = models.JSONField()

    class Meta:
        unique_together = ('strategy', 'indicator')


# 3. مدل بک‌تست و نتایج آن
class BacktestStatus(models.TextChoices):
    RUNNING = 'running', 'Running'
    COMPLETED = 'completed', 'Completed'
    FAILED = 'failed', 'Failed'


class Backtest(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    parameters = models.JSONField()
    result = models.JSONField()
    status = models.CharField(max_length=20, choices=BacktestStatus.choices)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-start_time']


# 4. مدل بات‌های معاملاتی (Bots)
class Bot(models.Model):
    name = models.CharField(max_length=255, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    strategy = models.ForeignKey(Strategy, on_delete=models.SET_NULL, null=True)
    symbol = models.CharField(max_length=50)
    exchange = models.CharField(max_length=50)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    max_trades = models.PositiveIntegerField(default=1)
    profit_limit = models.FloatField(null=True, blank=True)  # حد سود
    loss_limit = models.FloatField(null=True, blank=True)    # حد ضرر

    def __str__(self):
        return f'{self.name} ({self.symbol} on {self.exchange})'


# 5. مدل معاملات و سیگنال‌ها
class TradeStatus(models.TextChoices):
    OPEN = 'open', 'Open'
    CLOSED = 'closed', 'Closed'


class Trade(models.Model):
    bot = models.ForeignKey(Bot, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=50)
    entry_price = models.FloatField()
    exit_price = models.FloatField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=TradeStatus.choices)
    profit_loss = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']


class SignalType(models.TextChoices):
    BUY = 'buy', 'Buy'
    SELL = 'sell', 'Sell'


class Signal(models.Model):
    strategy = models.ForeignKey(Strategy, on_delete=models.CASCADE)
    symbol = models.CharField(max_length=50)
    signal_type = models.CharField(max_length=20, choices=SignalType.choices)
    confidence = models.FloatField()
    timestamp = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)

    class Meta:
        ordering = ['-timestamp']
