from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class Bookmark(TimeStampedModel):
    """
    UC-7.1.1 Bookmark Content.

    A reader saving an article to return to. Deliberately a join table with
    nothing on it but the pair and a timestamp: a bookmark is a fact, not an
    object with properties, and adding notes or folders would be inventing
    requirements nobody has stated.

    The unique constraint means saving twice is idempotent rather than
    producing duplicates, which lets the interface treat the control as a
    toggle without checking first.
    """

    reader = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="bookmarks",
    )
    article = models.ForeignKey(
        "editorial.Article",
        on_delete=models.CASCADE,
        related_name="bookmarked_by",
    )

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["reader", "article"],
                name="one_bookmark_per_reader_article",
            )
        ]
        indexes = [models.Index(fields=["reader", "-created_at"])]

    def __str__(self):
        return f"{self.reader_id} saved {self.article_id}"
