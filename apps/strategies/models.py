# apps/strategies/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from apps.core.models import BaseModel


class Strategy(BaseModel):
    """
    استراتژی‌های معاملاتی تعریف شده توسط کاربران.
    """
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="strategies",
        verbose_name=_("Owner")
    )
    name = models.CharField(
        max_length=128,
        verbose_name=_("Name")
    )
    description = models.TextField(
        blank=True,
        verbose_name=_("Description")
    )
    category = models.CharField(
        max_length=16,
        choices=[
            ('ENTRY', _('Entry Signal')),
            ('EXIT', _('Exit Signal')),
            ('FULL', _('Full Strategy')),
            ('RISK', _('Risk Model')),
            ('ML', _('ML Model')),
        ],
        default='FULL',
        verbose_name=_("Category")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )

    # زمان‌ها
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    def __str__(self):
        return f"{self.name} ({self.owner.email})"

    class Meta:
        verbose_name = _("Strategy")
        verbose_name_plural = _("Strategies")
        ordering = ["-created_at"]


class StrategyVersion(BaseModel):
    """
    نسخه‌های مختلف استراتژی‌ها برای حفظ تاریخچه و امکان بازگشت.
    """
    strategy = models.ForeignKey(
        Strategy,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name=_("Strategy")
    )
    version = models.CharField(
        max_length=32,
        verbose_name=_("Version")
    )
    parameters_schema = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Parameters Schema (JSON)")
    )
    indicator_configs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Indicator Configs (JSON)")
    )
    price_action_configs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Price Action Configs (JSON)")
    )
    smart_money_configs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("Smart Money Configs (JSON)")
    )
    ai_metrics_configs = models.JSONField(
        default=list,
        blank=True,
        verbose_name=_("AI Metrics Configs (JSON)")
    )
    is_approved_for_live = models.BooleanField(
        default=False,
        verbose_name=_("Is Approved for Live")
    )

    # زمان‌ها
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    def __str__(self):
        return f"{self.strategy.name} v{self.version}"

    class Meta:
        verbose_name = _("Strategy Version")
        verbose_name_plural = _("Strategy Versions")
        unique_together = ("strategy", "version")
        ordering = ["-created_at"]


class StrategyAssignment(BaseModel):
    """
    اتصال استراتژی‌ها به بات‌ها برای تعیین وزن و اولویت.
    """
    bot = models.ForeignKey(
        "bots.Bot",
        on_delete=models.CASCADE,
        related_name="strategy_assignments",
        verbose_name=_("Bot")
    )
    strategy_version = models.ForeignKey(
        StrategyVersion,
        on_delete=models.CASCADE,
        related_name="bot_assignments",
        verbose_name=_("Strategy Version")
    )
    weight = models.FloatField(
        default=1.0,
        verbose_name=_("Weight"),
        help_text=_("Weight of this strategy in the bot's final decision.")
    )
    priority = models.IntegerField(
        default=0,
        verbose_name=_("Priority"),
        help_text=_("Higher priority strategies are evaluated first.")
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name=_("Is Active")
    )
    parameters_override = models.JSONField(
        default=dict,
        blank=True,
        verbose_name=_("Parameters Override (JSON)"),
        help_text=_("Override default strategy parameters for this specific bot.")
    )

    # زمان‌ها
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created At")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated At")
    )

    def __str__(self):
        return f"{self.bot.name} - {self.strategy_version}"

    class Meta:
        verbose_name = _("Strategy Assignment")
        verbose_name_plural = _("Strategy Assignments")
        unique_together = ("bot", "strategy_version")
        ordering = ["-priority", "-weight"]