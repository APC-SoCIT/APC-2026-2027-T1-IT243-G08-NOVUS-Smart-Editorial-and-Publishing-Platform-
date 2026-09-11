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
