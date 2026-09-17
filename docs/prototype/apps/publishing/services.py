"""
UC-2.5 Execute Live Publishing.

Two paths, both owned by the Publisher:

* publish_issue  — the magazine. Every assigned article goes live together,
  or none does.
* publish_article — a standalone web piece between issues. Only permitted for
  an approved article that is NOT assigned to an issue; an article bound to an
  issue must wait for that issue, or it would appear before the magazine it
  belongs to.
"""
from django.db import transaction
from django.utils import timezone

from apps.editorial.models import Article


class NotReady(Exception):
    """Raised when a publication target fails its readiness check. Carries the
    reasons so the Publisher sees what to chase (UC-2.5 E1)."""

    def __init__(self, reasons):
        self.reasons = reasons if isinstance(reasons, list) else [reasons]
        super().__init__("; ".join(self.reasons))


@transaction.atomic
def publish_issue(issue, publisher):
    """Publishes the issue and all its articles atomically — a partial failure
    must never leave articles visible under an unpublished issue (UC-2.5 E2)."""
    from apps.issues.models import Issue

    if issue.status in (Issue.Status.PUBLISHED, Issue.Status.ARCHIVED):
        raise NotReady([f"Issue is already {issue.get_status_display().lower()}."])

    # UC-2.2: an issue goes to press closed. Publishing one whose contents
    # could still change is precisely what closing prevents, so leaving the
    # step optional would make the lock ceremony rather than a control.
    if issue.status == Issue.Status.PLANNING:
        raise NotReady([
            "This issue has not been closed. Close it to fix the table of "
            "contents, then publish."
        ])

    # The layout is the edition. An issue without one has nothing to
    # publish, so it gates release rather than only the download.
    if not issue.approved_design:
        raise NotReady([
            "This issue has no approved layout. The designer must submit the "
            "edition and an editor must approve it before the issue can be "
            "published."
        ])

    if not issue.is_ready:
        raise NotReady(issue.blocking_reasons())

    now = timezone.now()
    issue.articles.update(status=Article.Status.PUBLISHED, published_at=now)

    issue.status = Issue.Status.PUBLISHED
    issue.published_at = now
    issue.published_by = publisher
    issue.scheduled_for = None
    issue.save(update_fields=["status", "published_at", "published_by",
                              "scheduled_for", "updated_at"])

    from apps.notifications.models import Notification
    from apps.notifications.services import notify_many
    notify_many([a.writer for a in issue.articles.all()],
                Notification.Kind.PUBLISHED,
                f"{issue} is now live.", "/read")
    return issue


@transaction.atomic
def publish_article(article, publisher):
    """Publishes a standalone approved article not bound to an issue."""
    if article.status != Article.Status.APPROVED:
        raise NotReady([
            f"Article must be approved before publishing "
            f"(currently {article.get_status_display()})."
        ])

    if article.issue_id is not None:
        raise NotReady([
            f"This article is assigned to Issue #{article.issue.number} and "
            f"publishes with that issue. Unassign it to publish separately."
        ])

    article.status = Article.Status.PUBLISHED
    article.published_at = timezone.now()
    article.save(update_fields=["status", "published_at", "updated_at"])

    from apps.notifications.models import Notification
    from apps.notifications.services import notify
    notify(article.writer, Notification.Kind.PUBLISHED,
           f'"{article.title}" is now live.', f"/read/{article.id}")
    return article
