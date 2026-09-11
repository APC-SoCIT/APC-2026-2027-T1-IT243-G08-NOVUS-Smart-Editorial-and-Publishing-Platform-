from django.apps import AppConfig


class PublishingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.publishing"

    # No models yet — Phase 1 publishes a single Article directly (see
    # services.py). Phase 2 adds Issue/IssueFormat models here for true
    # UC-2.3 bundle publishing; nothing outside this app should need to
    # change when that happens (apps.editorial only calls publish_article()).
