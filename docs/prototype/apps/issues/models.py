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
    minimum_articles = models.PositiveSmallIntegerField(
        default=1,
        help_text='An issue below this count is not considered ready.',
    )
    title = models.CharField(max_length=200)
    target_release_date = models.DateField(null=True, blank=True)
    cover_image = models.ImageField(upload_to="covers/%Y/%m/", null=True, blank=True)

    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PLANNING
    )
    # UC-2.2 Compile Issue. Magazines call this closing an issue: the table
    # of contents is fixed so the art department can lay out pages knowing
    # they will not be redone. Reopening is permitted and recorded, because a
    # lock nobody can lift gets worked around rather than respected.
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="issues_closed",
    )
    reopen_reason = models.CharField(max_length=255, blank=True)

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
        """UC-2.5 precondition. The layout is the edition, so an issue is
        not ready until one is approved, however complete its copy."""
        return (
            self.approved_design is not None
            and self.total_articles >= self.minimum_articles
            and self.total_articles > 0
            and self.approved_articles == self.total_articles
        )

    @property
    def effective_cover(self):
        """The cover comes from the approved layout, falling back to any
        uploaded directly on the issue. The designer owns it, since they are
        already producing the artwork."""
        design = self.approved_design
        if design and design.cover_image:
            return design.cover_image
        return self.cover_image or None

    @property
    def is_closed(self):
        """A closed issue accepts no further articles. Publication and
        archival both leave it closed — it was never reopened, the issue
        simply moved on."""
        return self.status in (
            self.Status.COMPILED, self.Status.READY,
            self.Status.SCHEDULED, self.Status.PUBLISHED,
            self.Status.ARCHIVED,
        )

    @property
    def replica_available(self):
        """True when subscribers can download the print-style PDF."""
        return self.approved_design is not None

    def blocking_reasons(self):
        """Human-readable reasons publication is blocked (UC-2.5 E1), so the
        Publisher sees what to chase rather than a disabled button."""
        reasons = []
        if self.approved_design is None:
            reasons.append("No approved layout. The designer must submit the "
                           "edition and an editor must approve it.")
        if self.total_articles == 0:
            reasons.append("No articles have been assigned to this issue.")
        elif self.total_articles < self.minimum_articles:
            short = self.minimum_articles - self.total_articles
            reasons.append(
                f"This issue is planned for {self.minimum_articles} articles; "
                f"{short} more {'is' if short == 1 else 'are'} needed."
            )
        outstanding = self.total_articles - self.approved_articles
        if outstanding:
            reasons.append(
                f"{outstanding} of {self.total_articles} articles are not yet approved."
            )
        return reasons

    def replica_warnings(self):
        """Advisory notes only. A missing layout is no longer among them: it
        blocks publication and is reported by blocking_reasons."""
        return []
