from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    # Phase 3, Module 3: read-only aggregation endpoints over
    # apps.editorial / apps.ai_eval / apps.payments data — no new writes,
    # so this app should stay model-light (mostly views + serializers).
