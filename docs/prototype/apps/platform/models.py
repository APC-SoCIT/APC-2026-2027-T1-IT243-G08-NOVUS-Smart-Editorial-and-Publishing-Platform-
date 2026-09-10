from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class PlatformSetting(TimeStampedModel):
    """
    Module 4: Manage Platform Settings.

    A single row holds the platform's operational configuration. Secrets are
    deliberately absent — API keys and connection strings live in the
    environment, never in the database, so they cannot be read or altered
    through the web interface (UC-4.2 is therefore read-only status, not
    editable credentials).
    """

    # UC-4.1 Update Site Theme and Layout
    site_name = models.CharField(max_length=100, default="BOSS Magazine PH")
    tagline = models.CharField(max_length=200, blank=True)
    accent_colour = models.CharField(max_length=7, default="#1a2744")
    articles_per_page = models.PositiveSmallIntegerField(default=12)

    # UC-4.3 Toggle Maintenance Mode
    maintenance_mode = models.BooleanField(default=False)
    maintenance_message = models.CharField(
        max_length=255,
        default="BOSS Magazine is briefly unavailable while we make an update.",
    )

    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        verbose_name = "Platform settings"
        verbose_name_plural = "Platform settings"

    def __str__(self):
        return f"Platform settings ({'maintenance' if self.maintenance_mode else 'live'})"

    def save(self, *args, **kwargs):
        # Enforce a single row — configuration should never be ambiguous.
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
