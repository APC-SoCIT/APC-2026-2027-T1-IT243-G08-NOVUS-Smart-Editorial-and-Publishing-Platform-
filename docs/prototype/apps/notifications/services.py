"""
The single entry point for raising notifications. Every trigger in the register
calls notify(); nothing creates Notification rows directly, so muting and
email delivery stay in one place.

A notice goes to the app unless the person has turned that off or muted its
kind, and by email as well if they have turned email on. Email is sent once
the surrounding transaction commits: if the action that raised the notice is
rolled back, nobody is emailed about something that did not happen.
"""
from django.conf import settings
from django.db import transaction

from .models import Notification, NotificationPreference

SUBJECTS = {
    Notification.Kind.NEW_ISSUE: "A new issue of BOSS Magazine is out",
}


def notify(recipient, kind, message, link=""):
    """Raise a notification. Returns the in-app notice, or None."""
    if recipient is None:
        return None
    return _deliver([recipient], kind, message, link).get(recipient.pk)


def notify_many(recipients, kind, message, link=""):
    unique = {r.pk: r for r in recipients if r}
    _deliver(list(unique.values()), kind, message, link)


def _deliver(recipients, kind, message, link):
    shown, to_email = {}, []
    for r in recipients:
        pref = getattr(r, "notification_preference", None)
        if pref is None or pref.wants(kind):
            shown[r.pk] = Notification.objects.create(
                recipient=r, kind=kind, message=message, link=link)
        if pref is not None and pref.wants_email(kind) and r.email:
            to_email.append((r, shown.get(r.pk)))
    if to_email:
        transaction.on_commit(lambda: _email(to_email, kind, message, link))
    return shown


def _email(items, kind, message, link):
    from .email import send_many

    def settings_url(user):
        # Staff manage notices on their own page; readers in their account.
        page = "/account" if user.role == user.Role.READER else "/notifications"
        return settings.FRONTEND_URL + page

    send_many(
        [(r, {"message": message, "url": settings.FRONTEND_URL + (link or "/"),
              "settings_url": settings_url(r)}, n) for r, n in items],
        "notification",
        SUBJECTS.get(kind, f"NOVUS: {Notification.Kind(kind).label}"),
    )


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
