from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.payments"
    # Phase 2, Module 9: Subscription/Transaction models + PayMongo webhook
    # handler (UC-9.x). ReaderProfile.tier / payment_gateway_customer_id
    # (apps.accounts.models) already reserve the fields this will update.
