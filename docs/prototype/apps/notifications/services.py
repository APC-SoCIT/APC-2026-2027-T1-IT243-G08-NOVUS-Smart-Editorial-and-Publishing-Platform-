"""
The single entry point for raising notifications. Every trigger in the register
calls notify(); nothing creates Notification rows directly, so muting and
future email dispatch stay in one place.
"""
from .models import Notification, NotificationPreference


def notify(recipient, kind, message, link=""):
    """Raise a notification unless the recipient has muted this kind."""
    if recipient is None:
        return None

    pref = getattr(recipient, "notification_preference", None)
    if pref and not pref.wants(kind):
        return None

    return Notification.objects.create(
        recipient=recipient, kind=kind, message=message, link=link
    )


def notify_many(recipients, kind, message, link=""):
    seen = set()
    for r in recipients:
        if r and r.pk not in seen:
            seen.add(r.pk)
            notify(r, kind, message, link)


def article_link(user, article):
    """Where this person opens this article.

    A link written for one role sends another role into a workspace the
    route guard will refuse, so the link follows the recipient: writers go
    to the composer, designers to their article view, and editors, the
    publisher and the administrator to the review screen. An editor who
    wrote the article is its author here, so they go to the composer.
    """
    role, R = getattr(user, "role", None), user.Role
    if role == R.WRITER or (role == R.EDITOR and article.writer_id == user.id):
        return f"/writer/compose/{article.id}"
    if role == R.GRAPHIC_DESIGNER:
        return f"/designer/article/{article.id}"
    if role == R.READER:
        return f"/read/{article.id}"
    return f"/editor/review/{article.id}"
