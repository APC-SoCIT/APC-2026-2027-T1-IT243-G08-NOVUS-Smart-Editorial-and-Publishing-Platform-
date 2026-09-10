from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class MagazineDesign(TimeStampedModel):
    """
    UC-1.12 Upload Magazine Design / UC-1.15 Resubmit Magazine Design.

    One row per *version*. A resubmission never overwrites its predecessor —
    `version` is unique per design line, so the review history survives.

    Phase 1 stores files on local media. The container diagram specifies
    Cloudflare R2 for production; swapping is a storage-backend change in
    settings and does not touch this model.
    """

    class Status(models.TextChoices):
        PENDING_REVIEW = "PENDING_REVIEW", "Pending Editor Review"
        APPROVED = "APPROVED", "Approved"
        REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"
        SUPERSEDED = "SUPERSEDED", "Superseded"

    # Phase 2 replaces this with a FK to Issue (UC-2.2 Compile Issue).
    issue_label = models.CharField(
        max_length=100,
        help_text="Issue this layout belongs to, e.g. 'Issue #12'.",
    )
    version = models.CharField(max_length=20, default="v1.0")
    file = models.FileField(upload_to="designs/%Y/%m/")

    designer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="magazine_designs",
    )
    notes_to_editor = models.TextField(blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING_REVIEW
    )

    # UC-1.13 / UC-1.14: the Editor's verdict on this version.
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="design_reviews",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    revision_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["issue_label", "version"],
                name="unique_design_version_per_issue",
            )
        ]

    def __str__(self):
        return f"{self.issue_label} {self.version} ({self.status})"
