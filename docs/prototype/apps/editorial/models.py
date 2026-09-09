from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Article(TimeStampedModel):
    """Module 1: Manage Editorial Pipeline. Status values are the pipeline
    states referenced across UC-1.2 through UC-1.7 and UC-1.11."""

    class Status(models.TextChoices):
        DRAFTING = "DRAFTING", "Drafting"
        AWAITING_EVALUATION = "AWAITING_EVALUATION", "Awaiting Evaluation"
        UNDER_REVIEW = "UNDER_REVIEW", "Under Review"
        REVISION_REQUESTED = "REVISION_REQUESTED", "Revision Requested"
        APPROVED = "APPROVED", "Approved"
        PUBLISHED = "PUBLISHED", "Published"
        WITHDRAWN = "WITHDRAWN", "Withdrawn"

    title = models.CharField(max_length=255)
    body = models.TextField()
    category = models.CharField(max_length=100, blank=True)
    tags = models.CharField(max_length=255, blank=True)  # comma-separated for the MVP
    status = models.CharField(max_length=25, choices=Status.choices, default=Status.DRAFTING)

    writer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="written_articles"
    )
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="edited_articles",
    )

    published_at = models.DateTimeField(null=True, blank=True)
    withdrawal_reason = models.CharField(max_length=255, blank=True)  # UC-1.7, Phase 2

    def __str__(self):
        return f"{self.title} [{self.status}]"


class RevisionNote(TimeStampedModel):
    """UC-1.4 Request Revision. Mirrors the 'Revision Note Composer' screen
    in the Release-1 wireframes exactly (section / note type / instruction /
    priority)."""

    class NoteType(models.TextChoices):
        GRAMMAR = "GRAMMAR", "Grammar"
        TONE = "TONE", "Tone"
        STRUCTURE = "STRUCTURE", "Structure"
        FACTUAL = "FACTUAL", "Factual"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"

    article = models.ForeignKey(Article, on_delete=models.CASCADE, related_name="revision_notes")
    editor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    section = models.CharField(max_length=100, blank=True)
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.STRUCTURE)
    instruction = models.CharField(max_length=500)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    def __str__(self):
        return f"RevisionNote<{self.article_id}> {self.note_type}"
