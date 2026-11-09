"""
Django email backend for Resend's HTTPS API.

Using the API rather than Resend's SMTP relay means mail goes out on port
443, which every host allows; some hosting tiers block outbound SMTP ports.
Because it is a normal Django backend, the rest of the code just calls
Django's email functions, and tests use Django's in-memory backend instead.

Several messages at once (a new issue going to every subscriber) go through
Resend's batch endpoint, up to 100 per call, so a large send is a handful of
requests rather than one per reader.
"""
import logging

import httpx
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

log = logging.getLogger(__name__)

API_URL = "https://api.resend.com/emails"
BATCH_URL = "https://api.resend.com/emails/batch"
BATCH_SIZE = 100  # Resend's limit per batch call


class ResendEmailBackend(BaseEmailBackend):
    """Sets provider_message_id on each message it sends. With
    fail_silently, a message that could not be sent gets send_error instead
    of raising, so the caller can record each outcome."""

    def __init__(self, api_key=None, timeout=10, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = api_key or getattr(settings, "RESEND_API_KEY", "")
        self.timeout = timeout

    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        with httpx.Client(timeout=self.timeout) as client:
            for i in range(0, len(email_messages), BATCH_SIZE):
                chunk = email_messages[i:i + BATCH_SIZE]
                try:
                    ids = (self._send_batch(client, chunk) if len(chunk) > 1
                           else [self._send(client, chunk[0])])
                except Exception as exc:
                    log.exception("Resend could not send %d message(s)", len(chunk))
                    if not self.fail_silently:
                        raise
                    for message in chunk:
                        message.send_error = str(exc)
                    continue
                for message, message_id in zip(chunk, ids):
                    message.provider_message_id = message_id
                sent += len(chunk)
        return sent

    def _post(self, client, url, payload):
        response = client.post(url, json=payload,
                               headers={"Authorization": f"Bearer {self.api_key}"})
        if response.status_code >= 400:
            raise RuntimeError(f"Resend returned {response.status_code}: {response.text[:200]}")
        return response.json()

    def _send(self, client, message):
        return self._post(client, API_URL, self._payload(message)).get("id", "")

    def _send_batch(self, client, messages):
        data = self._post(client, BATCH_URL, [self._payload(m) for m in messages])
        return [item.get("id", "") for item in data.get("data", [])] + [""] * len(messages)

    @staticmethod
    def _payload(message):
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
        return payload
