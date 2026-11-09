"""
The single entry point for sending email. Every message is recorded as an
EmailDispatch before it is sent, and the record is updated with the result,
so a failure is visible in the admin rather than lost.

Sending never raises: a caller such as password recovery must give the user
the same answer whether or not the email went out.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailDispatch

log = logging.getLogger(__name__)

FIELDS = ["status", "sent_at", "provider_message_id", "attempts", "last_error", "updated_at"]


def send_email(recipient, template, subject, context=None, notification=None):
    """Render email/<template>.txt and .html, send them, and record the result."""
    return send_many([(recipient, context, notification)], template, subject)[0]


def send_many(items, template, subject):
    """Send one template to several people in one go.

    items is a list of (recipient, context, notification). Each gets its own
    EmailDispatch and its own outcome; the backend groups the sending.
    """
    dispatches, messages = [], []
    for recipient, context, notification in items:
        dispatch = EmailDispatch.objects.create(
            recipient=recipient, to_address=recipient.email, subject=subject,
            template=template, notification=notification)
        dispatches.append(dispatch)
        try:
            ctx = {"user": recipient, "site_name": "BOSS Magazine PH",
                   "frontend_url": settings.FRONTEND_URL, **(context or {})}
            text = render_to_string(f"email/{template}.txt", ctx)
            html = render_to_string(f"email/{template}.html", ctx)
            message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL,
                                             [recipient.email])
            message.attach_alternative(html, "text/html")
        except Exception as exc:  # noqa: BLE001 - recorded, never raised
            log.exception("Email %s to user %s could not be built", template, recipient.pk)
            message = None
            dispatch.last_error = str(exc)[:255]
        messages.append(message)

    ready = [m for m in messages if m is not None]
    failure = ""
    try:
        get_connection(fail_silently=True).send_messages(ready)
    except Exception as exc:  # noqa: BLE001 - a backend that raises anyway
        log.exception("Email %s could not be sent", template)
        failure = str(exc)

    now = timezone.now()
    for dispatch, message in zip(dispatches, messages):
        error = (dispatch.last_error if message is None
                 else failure or getattr(message, "send_error", ""))
        if error:
            dispatch.status = EmailDispatch.Status.FAILED
            dispatch.last_error = error[:255]
        else:
            dispatch.status = EmailDispatch.Status.SENT
            dispatch.sent_at = now
            dispatch.provider_message_id = (getattr(message, "provider_message_id", "") or "")[:100]
        dispatch.attempts += 1
        dispatch.save(update_fields=FIELDS)
    return dispatches
