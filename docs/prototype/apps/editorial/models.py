from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Article(TimeStampedModel):
    """Module 1: Manage Editorial Pipeline. Status values are the pipeline
    states referenced across UC-1.2 through UC-1.7 and UC-1.11."""

    class Status(models.TextChoices):
        ASSIGNED = "ASSIGNED", "Assigned"
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

    # True when the AI pre-screening gate returned this article rather than
    # an Editor (UC-1.5). Recorded explicitly rather than inferred from the
    # revision notes, because a failing submission may carry no suggestions.
    returned_by_ai = models.BooleanField(default=False)

    # UC-1.11 Assign Article to Issue. Null until an Editor assigns it;
    # an article cannot be published outside an issue (UC-2.5).
    issue = models.ForeignKey(
        "issues.Issue", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="articles",
    )
    issue_order = models.PositiveSmallIntegerField(default=0)

    # UC-1.1 Assign Article. Null when a Writer started the piece themselves —
    # both routes are permitted (UC-1.2 has no assignment precondition).
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="articles_assigned",
    )
    brief = models.TextField(
        blank=True,
        help_text="The topic, angle, and editorial direction given to the Writer.",
    )
    deadline = models.DateField(null=True, blank=True)

    # --- Web presentation ---------------------------------------------------
    # Photography is editorial, not design: the Writer supplies it and the
    # Editor may replace it. The Designer composes with these images for the
    # print replica but does not source them. All optional — opinion pieces
    # and short news often run text-only.
    hero_image = models.ImageField(upload_to="articles/%Y/%m/", null=True, blank=True)
    hero_caption = models.CharField(max_length=255, blank=True)
    excerpt = models.CharField(
        max_length=300, blank=True,
        help_text="Standfirst shown under the headline and on cards.",
    )
    slug = models.SlugField(max_length=220, unique=True, null=True, blank=True)

    # Promoted to the homepage hero. Requires an image — a featured article
    # without one renders as an empty banner.
    is_featured = models.BooleanField(default=False)

    # UC-8.2 Access Premium Articles. Articles bound to an issue are the paid
    # product and default to premium on assignment; standalone web pieces are
    # free and drive traffic. An Editor can override either way.
    is_premium = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.slug and self.title:
            from django.utils.text import slugify
            base = slugify(self.title)[:200] or "article"
            slug, n = base, 2
            while Article.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def word_count(self):
        from django.utils.html import strip_tags
        return len(strip_tags(self.body or "").split())

    @property
    def reading_time(self):
        """Minutes, at 200 wpm — the convention most publications use."""
        return max(1, round(self.word_count / 200))

    @property
    def is_overdue(self):
        """Drives the overdue counts on the pipeline dashboards."""
        from django.utils import timezone
        if not self.deadline or self.status in (
            self.Status.PUBLISHED, self.Status.WITHDRAWN, self.Status.APPROVED
        ):
            return False
        return self.deadline < timezone.now().date()

    @property
    def days_to_deadline(self):
        from django.utils import timezone
        if not self.deadline:
            return None
        return (self.deadline - timezone.now().date()).days

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
    # Null when the note was generated by the AI pre-screening gate (UC-1.5)
    # rather than written by an Editor (UC-1.7).
    editor = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True
    )
    section = models.CharField(max_length=100, blank=True)
    note_type = models.CharField(max_length=20, choices=NoteType.choices, default=NoteType.STRUCTURE)
    instruction = models.CharField(max_length=500)
    priority = models.CharField(max_length=10, choices=Priority.choices, default=Priority.MEDIUM)

    def __str__(self):
        return f"RevisionNote<{self.article_id}> {self.note_type}"


class ArticleImage(TimeStampedModel):
    """Images used inside an article body, and handed to the Designer for the
    print replica. Uploaded by the Writer or Editor during composition."""

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="articles/%Y/%m/")
    caption = models.CharField(max_length=255, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Image for {self.article_id}"


class ArticleVersion(TimeStampedModel):
    """A snapshot of an article's content at submission (UC-1.4).

    Taken on every submit so the Editor can see what changed between drafts
    and the Writer can recover superseded copy. Without this the revision loop
    silently loses the previous draft.
    """

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name="versions"
    )
    number = models.PositiveSmallIntegerField()
    title = models.CharField(max_length=200)
    body = models.TextField()
    excerpt = models.CharField(max_length=300, blank=True)
    submitted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True
    )

    class Meta:
        ordering = ["-number"]
        unique_together = [("article", "number")]

    def __str__(self):
        return f"{self.article_id} v{self.number}"

    @property
    def word_count(self):
        from django.utils.html import strip_tags
        return len(strip_tags(self.body or "").split())
