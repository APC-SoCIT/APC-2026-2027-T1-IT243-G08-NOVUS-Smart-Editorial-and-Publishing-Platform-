"""
Subscriptions and the payments that pay for them (UC-4.3, UC-4.4).

PayRex's signed notification is the authority on whether a payment
happened, not the reader's return to the site: a browser redirect can be
lost, repeated or forged. Access is granted only when a notification has
been verified (see views.PaymentWebhookView).
"""
from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Subscription(TimeStampedModel):
    """One reader's subscription and the period it is paid up to.

    A renewal extends the same record rather than adding a new one, so a
    reader has one subscription with a growing paid-up date.
    """

    class Plan(models.TextChoices):
        MONTHLY = "MONTHLY", "Monthly"
        ANNUAL = "ANNUAL", "Annual"

    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past due"     # kept for automatic billing, unused while prepaid
        CANCELLED = "CANCELLED", "Cancelled"  # access continues to current_period_end
        EXPIRED = "EXPIRED", "Expired"

    reader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="subscriptions")
    plan = models.CharField(max_length=30, choices=Plan.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    provider = models.CharField(max_length=30, default="payrex")
    provider_subscription_id = models.CharField(max_length=100, unique=True)

    current_period_start = models.DateTimeField()
    # Access continues to this moment, even after cancellation (BR-11).
    current_period_end = models.DateTimeField()
    cancelled_at = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False)
    # The renewal reminder is sent once per period.
    reminder_sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["reader", "status"], name="active_subscription_lookup")]

    def __str__(self):
        return f"{self.reader} {self.plan} {self.status} to {self.current_period_end:%Y-%m-%d}"


class Transaction(TimeStampedModel):
    """One payment confirmed by PayRex.

    provider_transaction_id is unique, which is what stops a repeated
    notification from being recorded, or granting access, twice.
    """

    class Kind(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        REFUND = "REFUND", "Refund"
        CHARGEBACK = "CHARGEBACK", "Chargeback"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        REFUNDED = "REFUNDED", "Refunded"

    subscription = models.ForeignKey(Subscription, null=True, blank=True,
                                     on_delete=models.SET_NULL, related_name="transactions")
    reader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                               related_name="transactions")

    provider_transaction_id = models.CharField(max_length=100, unique=True)
    # Our checkout reference, so the reader's return page can find the result.
    reference = models.CharField(max_length=40, db_index=True)
    kind = models.CharField(max_length=20, choices=Kind.choices, default=Kind.PAYMENT)
    status = models.CharField(max_length=20, choices=Status.choices)
    plan = models.CharField(max_length=30, choices=Subscription.Plan.choices)

    amount_cents = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="PHP")
    payment_method = models.CharField(max_length=30, blank=True)

    # Kept for diagnosis; never shown to the reader.
    failure_code = models.CharField(max_length=50, blank=True)
    raw_payload = models.JSONField()

    occurred_at = models.DateTimeField()

    class Meta:
        ordering = ["-occurred_at"]
        indexes = [
            models.Index(fields=["reader", "occurred_at"], name="reader_payment_history"),
            models.Index(fields=["status", "occurred_at"], name="revenue_reporting"),
        ]

    def __str__(self):
        return f"{self.provider_transaction_id} {self.status} {self.amount_cents}"
