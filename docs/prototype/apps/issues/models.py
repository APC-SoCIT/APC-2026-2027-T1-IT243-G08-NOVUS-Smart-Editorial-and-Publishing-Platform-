from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Issue(TimeStampedModel):
    """
    UC-2.2 Compile Issue / UC-2.5 Execute Live Publishing.

    An Issue is the unit BOSS Magazine actually publishes: a set of approved
    articles bound to an approved layout and released on a target date.
    Created by the Publisher (UC-2.1); articles are assigned to it by an
    Editor (UC-1.11).
    """

    class Status(models.TextChoices):
        PLANNING = "PLANNING", "Planning"
        COMPILED = "COMPILED", "Compiled"
        READY = "READY", "Ready to Publish"
        SCHEDULED = "SCHEDULED", "Scheduled"
        PUBLISHED = "PUBLISHED", "Published"
        ARCHIVED = "ARCHIVED", "Archived"

    number = models.PositiveIntegerField(unique=True)
    title = models.CharField(max_length=200)
    target_release_date = models.DateField(null=True, blank=True)
    cover_image = models.ImageField(upload_to="covers/%Y/%m/", null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNING
    )
    scheduled_for = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="issues_created",
    )
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="issues_published",
    )

    class Meta:
        ordering = ["-number"]

    def __str__(self):
        return f"Issue #{self.number} — {self.title}"

    # --- readiness (drives the Publisher pipeline view and blocks publishing) ---

    @property
    def total_articles(self):
        return self.articles.count()

    @property
    def approved_articles(self):
        from apps.editorial.models import Article
        return self.articles.filter(
            status__in=[Article.Status.APPROVED, Article.Status.PUBLISHED]
        ).count()

    @property
    def approved_design(self):
        from apps.design.models import MagazineDesign
        return self.designs.filter(status=MagazineDesign.Status.APPROVED).first()

    @property
    def is_ready(self):
        """UC-2.5 precondition. The web edition needs approved copy only —
        an approved layout gates the downloadable replica (UC-8.1), not the
        articles, which publish as responsive web pages regardless."""
        return (
            self.total_articles > 0
            and self.approved_articles == self.total_articles
        )

    @property
    def replica_available(self):
        """True when subscribers can download the print-style PDF."""
        return self.approved_design is not None

    def blocking_reasons(self):
        """Human-readable reasons publication is blocked (UC-2.5 E1), so the
        Publisher sees what to chase rather than a disabled button."""
        reasons = []
        if self.total_articles == 0:
            reasons.append("No articles have been assigned to this issue.")
        outstanding = self.total_articles - self.approved_articles
        if outstanding:
            reasons.append(
                f"{outstanding} of {self.total_articles} articles are not yet approved."
            )
        return reasons

    def replica_warnings(self):
        """Not blocking — the issue can publish to the web without a layout,
        but subscribers get no downloadable replica."""
        if self.approved_design is None:
            return ["No approved layout, so this issue will publish to the "
                    "web without a downloadable digital edition."]
        return []
