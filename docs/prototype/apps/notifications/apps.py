from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    # Phase 2, Module 10: Notification model + Resend wiring (UC-10.x).
    # Trigger points already exist in the code as comments:
    #   apps/publishing/services.py -> after publish
    #   apps/editorial/views.py     -> after request_revision / approve
