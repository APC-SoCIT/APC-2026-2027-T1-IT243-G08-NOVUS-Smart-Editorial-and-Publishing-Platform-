from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Notification(TimeStampedModel):
    """
    UC-10.1 View Notifications.

    Raised by the events enumerated in the notification trigger register:
    assignment, submission, revision requests, approvals, design review,
    publication, and deadline warnings. In-app only in this release; email
    dispatch via Resend is Phase 2 (UC-2.6).
    """

    class Kind(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Article assigned"
        SUBMITTED = "SUBMITTED", "Article submitted"
        REVISION = "REVISION", "Revision requested"
        APPROVED = "APPROVED", "Article approved"
        RETURNED_BY_AI = "RETURNED_BY_AI", "Returned by pre-screening"
        DESIGN_UPLOADED = "DESIGN_UPLOADED", "Layout submitted"
        DESIGN_REVISION = "DESIGN_REVISION", "Design revision requested"
        DESIGN_APPROVED = "DESIGN_APPROVED", "Layout approved"
        PUBLISHED = "PUBLISHED", "Published"
        DEADLINE_NEAR = "DEADLINE_NEAR", "Deadline approaching"
        DEADLINE_PASSED = "DEADLINE_PASSED", "Deadline passed"
        MESSAGE = "MESSAGE", "New message"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    kind = models.CharField(max_length=20, choices=Kind.choices)
    message = models.CharField(max_length=255)

    # Where clicking the notification should take the user.
    link = models.CharField(max_length=200, blank=True)

    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["recipient", "is_read"])]

    def __str__(self):
        return f"{self.get_kind_display()} -> {self.recipient_id}"


class NotificationPreference(TimeStampedModel):
    """UC-10.3. Security and account notices are always delivered regardless."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    in_app = models.BooleanField(default=True)
    email = models.BooleanField(default=False)  # Phase 2
    muted_kinds = models.JSONField(default=list, blank=True)

    def wants(self, kind):
        return self.in_app and kind not in (self.muted_kinds or [])
