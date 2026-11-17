"""
The two things NOVUS asks of PayMongo: open a hosted checkout, and prove that
a notification came from PayMongo.

Payment details are entered on PayMongo's own checkout page, so card numbers
and e-wallet sign-ins never reach NOVUS.
"""
import hashlib
import hmac

import httpx
from django.conf import settings

API = "https://api.paymongo.com/v1"


class PayMongoError(Exception):
    """PayMongo refused the request or could not be reached."""


def configured():
    """Both keys are needed: without the webhook secret a reader could pay
    and never be granted access, because no notification could be trusted."""
    return bool(settings.PAYMONGO_SECRET_KEY and settings.PAYMONGO_WEBHOOK_SECRET)


def live():
    return settings.PAYMONGO_SECRET_KEY.startswith("sk_live_")


def _post(path, attributes):
    try:
        response = httpx.post(
            f"{API}{path}", json={"data": {"attributes": attributes}},
            auth=(settings.PAYMONGO_SECRET_KEY, ""), timeout=15,
        )
    except httpx.HTTPError as exc:
        raise PayMongoError(f"PayMongo could not be reached: {exc}") from exc
    if response.status_code >= 400:
        raise PayMongoError(f"PayMongo returned {response.status_code}: {response.text[:300]}")
    return response.json()["data"]


def create_checkout(*, reader, plan, reference, success_url, cancel_url):
    """Open a hosted checkout for one plan. Returns (session id, checkout URL).

    The reader and plan travel in the metadata, which PayMongo returns in the
    signed notification. NOVUS set them, and the signature proves they were
    not changed on the way back.
    """
    data = _post("/checkout_sessions", {
        "line_items": [{
            "name": f"BOSS Magazine: {plan.name} subscription",
            "description": f"{plan.days} days of subscriber access",
            "amount": plan.amount,
            "currency": "PHP",
            "quantity": 1,
        }],
        "payment_method_types": settings.PAYMONGO_PAYMENT_METHODS,
        "description": f"BOSS Magazine {plan.name} subscription",
        "reference_number": reference,
        "billing": {"name": reader.get_full_name() or reader.email, "email": reader.email},
        "send_email_receipt": True,
        "show_description": True,
        "show_line_items": True,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {"reader_id": str(reader.pk), "plan": plan.code, "reference": reference},
    })
    return data["id"], data["attributes"]["checkout_url"]


def create_webhook(url, events):
    """Register NOVUS's notification address. PayMongo answers with the
    secret that signs every notification sent to it."""
    data = _post("/webhooks", {"url": url, "events": events})
    return data["id"], data["attributes"].get("secret_key", "")


def signature_ok(header, body):
    """True when the Paymongo-Signature header proves PayMongo sent body.

    The header reads t=<timestamp>,te=<test signature>,li=<live signature>.
    The signature is an HMAC-SHA256, keyed with the webhook's secret, of the
    timestamp, a full stop and the raw request body. Test-mode keys are
    checked against te, live keys against li.
    """
    secret = settings.PAYMONGO_WEBHOOK_SECRET
    if not secret or not header:
        return False
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    timestamp = parts.get("t", "")
    supplied = parts.get("li" if live() else "te", "")
    if not timestamp or not supplied:
        return False
    signed = timestamp.encode() + b"." + body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def sign(body, timestamp="1700000000"):
    """Make a header the way PayMongo does. Used by the tests and by the
    simulate_payment command for trying the flow without a real payment."""
    digest = hmac.new(settings.PAYMONGO_WEBHOOK_SECRET.encode(),
                      timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    key = "li" if live() else "te"
    other = "te" if key == "li" else "li"
    return f"t={timestamp},{key}={digest},{other}="
