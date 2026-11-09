"""
The single entry point for sending email. Every message is recorded as an
EmailDispatch before it is sent, and the record is updated with the result,
so a failure is visible in the admin rather than lost.

Sending never raises: a caller such as password recovery must give the user
the same answer whether or not the email went out.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from .models import EmailDispatch

log = logging.getLogger(__name__)


def send_email(recipient, template, subject, context=None, notification=None):
    """Render email/<template>.txt and .html, send them, and record the result."""
    context = {"user": recipient, "site_name": "BOSS Magazine PH", **(context or {})}
    dispatch = EmailDispatch.objects.create(
        recipient=recipient, to_address=recipient.email, subject=subject,
        template=template, notification=notification)

    try:
        text = render_to_string(f"email/{template}.txt", context)
        html = render_to_string(f"email/{template}.html", context)
        message = EmailMultiAlternatives(subject, text, settings.DEFAULT_FROM_EMAIL, [recipient.email])
        message.attach_alternative(html, "text/html")
        message.send()
    except Exception as exc:  # noqa: BLE001 - recorded, never raised
        log.exception("Email %s to user %s failed", template, recipient.pk)
        dispatch.status = EmailDispatch.Status.FAILED
        dispatch.last_error = str(exc)[:255]
    else:
        dispatch.status = EmailDispatch.Status.SENT
        dispatch.sent_at = timezone.now()
        dispatch.provider_message_id = getattr(message, "provider_message_id", "")[:100]
    dispatch.attempts += 1
    dispatch.save(update_fields=["status", "sent_at", "provider_message_id", "attempts", "last_error", "updated_at"])
    return dispatch
