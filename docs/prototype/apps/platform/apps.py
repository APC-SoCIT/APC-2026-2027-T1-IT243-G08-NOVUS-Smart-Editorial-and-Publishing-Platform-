from django.apps import AppConfig


class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.platform"
    # Phase 3, Module 4/5: PlatformSetting model + Admin user-management
    # endpoints (UC-4.x, UC-5.x). apps.accounts.User already has the fields
    # UC-5.2.2/5.2.3 need (is_suspended, must_reset_password).
