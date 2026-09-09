"""
UC-2.3 Execute Live Publishing — simplified for Phase 1 to publish a single
Article rather than a bundled Issue (see README "Deliberate MVP
simplification"). Called only from apps.editorial.views.ArticleViewSet.publish
so that swapping this for real Issue-bundle publishing in Phase 2 is a
one-file change.
"""
from django.utils import timezone

from apps.editorial.models import Article


def publish_article(article: Article) -> Article:
    if article.status != Article.Status.APPROVED:
        raise ValueError(
            f"Article must be APPROVED before publishing (currently {article.status})."
        )
    article.status = Article.Status.PUBLISHED
    article.published_at = timezone.now()
    article.save(update_fields=["status", "published_at", "updated_at"])
    # Phase 2: dispatch a "Delivery Status" notification here via
    # apps.notifications once that app has a real send path (Resend).
    return article
