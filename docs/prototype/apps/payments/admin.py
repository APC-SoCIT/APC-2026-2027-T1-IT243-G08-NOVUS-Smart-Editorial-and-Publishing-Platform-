from django.contrib import admin

from .models import Subscription, Transaction


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["reader", "plan", "status", "current_period_end", "cancel_at_period_end"]
    list_filter = ["status", "plan"]
    search_fields = ["reader__email"]
    readonly_fields = ["provider", "provider_subscription_id", "created_at", "updated_at"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Read-only: a transaction is PayMongo's record, not ours to edit.
    Refunds are issued in the PayMongo dashboard."""

    list_display = ["occurred_at", "reader", "plan", "amount_cents", "payment_method",
                    "status", "failure_code"]
    list_filter = ["status", "plan", "payment_method"]
    search_fields = ["reader__email", "provider_transaction_id", "reference"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
