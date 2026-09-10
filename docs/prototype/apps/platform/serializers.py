from django.conf import settings as dj
from rest_framework import serializers

from .models import PlatformSetting


class PlatformSettingSerializer(serializers.ModelSerializer):
    integrations = serializers.SerializerMethodField()

    class Meta:
        model = PlatformSetting
        fields = [
            "site_name", "tagline", "accent_colour", "articles_per_page",
            "maintenance_mode", "maintenance_message",
            "integrations", "updated_at",
        ]
        read_only_fields = ["integrations", "updated_at"]

    def get_integrations(self, obj):
        """UC-4.2: status only. Credentials are held in the environment and are
        never returned, so this reports whether each integration is configured
        without exposing what it is configured with."""
        key = getattr(dj, "ANTHROPIC_API_KEY", "") or ""
        ai_live = bool(key) and "placeholder" not in key

        return [
            {"name": "Anthropic Claude",
             "purpose": "Article pre-screening and editorial briefs",
             "configured": ai_live,
             "detail": (f"Model: {dj.ANTHROPIC_EVAL_MODEL}" if ai_live
                        else "No API key set — evaluations return a stub")},
            {"name": "PostgreSQL",
             "purpose": "Primary data store",
             "configured": "postgresql" in dj.DATABASES["default"]["ENGINE"],
             "detail": dj.DATABASES["default"].get("HOST") or "local"},
            {"name": "Cloudflare R2",
             "purpose": "Magazine designs and article media",
             "configured": False,
             "detail": "Phase 2 — files are on local storage"},
            {"name": "PayMongo",
             "purpose": "Subscription payments",
             "configured": False,
             "detail": "Phase 2 — subscription tiers granted manually"},
            {"name": "Resend",
             "purpose": "Transactional email",
             "configured": False,
             "detail": "Phase 2 — notifications are in-app only"},
        ]
