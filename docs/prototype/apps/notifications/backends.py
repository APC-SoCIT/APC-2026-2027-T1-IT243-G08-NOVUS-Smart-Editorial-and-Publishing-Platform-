"""
Django email backend for Resend's HTTPS API.

Using the API rather than Resend's SMTP relay means mail goes out on port
443, which every host allows; some hosting tiers block outbound SMTP ports.
Because it is a normal Django backend, the rest of the code just calls
Django's email functions, and tests use Django's in-memory backend instead.
"""
import logging

import httpx
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"


class ResendEmailBackend(BaseEmailBackend):
    def __init__(self, api_key=None, timeout=10, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, "RESEND_API_KEY", "")
        self.timeout = timeout

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        with httpx.Client(timeout=self.timeout) as client:
            for message in email_messages:
                try:
                    message.provider_message_id = self._send(client, message)
                    sent += 1
                except Exception:
                    log.exception("Resend could not send to %s", message.to)
                    if not self.fail_silently:
                        raise
        return sent

    def _send(self, client, message):
        payload = {
            "from": message.from_email,
            "to": list(message.to),
            "subject": message.subject,
            "text": message.body,
        }
        for content, mimetype in getattr(message, "alternatives", []):
            if mimetype == "text/html":
                payload["html"] = content
        if message.reply_to:
            payload["reply_to"] = list(message.reply_to)
        response = client.post(API_URL, json=payload,
                               headers={"Authorization": f"Bearer {self.api_key}"})
        if response.status_code >= 400:
            raise RuntimeError(f"Resend returned {response.status_code}: {response.text[:200]}")
        return response.json().get("id", "")
