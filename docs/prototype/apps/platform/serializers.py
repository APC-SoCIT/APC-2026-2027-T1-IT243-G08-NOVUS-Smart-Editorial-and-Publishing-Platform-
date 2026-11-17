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
             "configured": dj.USE_R2,
             "detail": (dj.R2_BUCKET_NAME if dj.USE_R2
                        else "Not configured — files are on local storage, "
                             "which the hosting filesystem erases on redeploy")},
            {"name": "PayRex",
             "purpose": "Subscription payments",
             "configured": bool(dj.PAYREX_SECRET_KEY and dj.PAYREX_WEBHOOK_SECRET),
             "detail": (("Live mode" if dj.PAYREX_SECRET_KEY.startswith("sk_live")
                         else "Test mode: nothing is charged")
                        if dj.PAYREX_SECRET_KEY and dj.PAYREX_WEBHOOK_SECRET
                        else "Not configured: set PAYREX_SECRET_KEY and "
                             "PAYREX_WEBHOOK_SECRET")},
            {"name": "Resend",
             "purpose": "Transactional email",
             "configured": bool(dj.RESEND_API_KEY),
             "detail": (f"Sending as {dj.DEFAULT_FROM_EMAIL}" if dj.RESEND_API_KEY
                        else "Not configured: emails are printed to the server log")},
        ]
