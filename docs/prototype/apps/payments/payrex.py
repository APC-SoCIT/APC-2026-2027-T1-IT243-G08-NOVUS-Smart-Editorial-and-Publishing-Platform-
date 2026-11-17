"""
The two things NOVUS asks of PayRex: open a hosted checkout, and prove that
a notification came from PayRex.

Payment details are entered on PayRex's own checkout page, so card numbers
and e-wallet sign-ins never reach NOVUS.

PayRex takes form fields, not JSON, with nested values written as
line_items[][name] and metadata[key], and the secret key as the username of
HTTP basic authentication.
"""
import hashlib
import hmac

import httpx
from django.conf import settings

API = "https://api.payrexhq.com"
PAID_EVENT = "payment_intent.succeeded"


class PayRexError(Exception):
    """PayRex refused the request or could not be reached."""


def configured():
    """Both keys are needed: without the webhook secret a reader could pay
    and never be granted access, because no notification could be trusted."""
    return bool(settings.PAYREX_SECRET_KEY and settings.PAYREX_WEBHOOK_SECRET)


def live():
    return settings.PAYREX_SECRET_KEY.startswith("sk_live")


def form(fields):
    """Flatten nested values the way PayRex reads them:
    {"line_items": [{"name": "x"}], "metadata": {"a": "1"}, "payment_methods": ["gcash"]}
    becomes line_items[][name]=x, metadata[a]=1, payment_methods[]=gcash."""
    out = []
    for key, value in fields.items():
        if isinstance(value, dict):
            out += [(f"{key}[{k}]", str(v)) for k, v in value.items()]
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    out += [(f"{key}[][{k}]", str(v)) for k, v in item.items()]
                else:
                    out.append((f"{key}[]", str(item)))
        else:
            out.append((key, str(value)))
    return out


def _post(path, fields):
    try:
        response = httpx.post(f"{API}{path}", data=form(fields),
                              auth=(settings.PAYREX_SECRET_KEY, ""), timeout=15)
    except httpx.HTTPError as exc:
        raise PayRexError(f"PayRex could not be reached: {exc}") from exc
    if response.status_code >= 400:
        raise PayRexError(f"PayRex returned {response.status_code}: {response.text[:300]}")
    return response.json()


def create_checkout(*, reader, plan, reference, success_url, cancel_url):
    """Open a hosted checkout for one plan. Returns (session id, checkout URL).

    The reader and plan travel in the metadata, which PayRex copies onto the
    payment it creates and returns in the signed notification. NOVUS set
    them, and the signature proves they were not changed on the way back.
    """
    data = _post("/checkout_sessions", {
        "currency": "PHP",
        "line_items": [{
            "name": f"BOSS Magazine: {plan.name} subscription",
            "description": f"{plan.days} days of subscriber access",
            "amount": plan.amount,
            "quantity": 1,
        }],
        "payment_methods": settings.PAYREX_PAYMENT_METHODS,
        "success_url": success_url,
        "cancel_url": cancel_url,
        "customer_reference_id": reference,
        "description": f"BOSS Magazine {plan.name} subscription ({reference})",
        "metadata": {"reader_id": reader.pk, "plan": plan.code, "reference": reference},
    })
    return data["id"], data["url"]


def create_webhook(url, events):
    """Register NOVUS's notification address. PayRex answers with the secret
    that signs every notification sent to it."""
    data = _post("/webhooks", {"url": url, "events": events,
                               "description": "NOVUS subscription payments"})
    return data["id"], data.get("secret_key", "")


def signature_ok(header, body):
    """True when the Payrex-Signature header proves PayRex sent body.

    The header reads t=<timestamp>,te=<test signature>,li=<live signature>.
    The signature is an HMAC-SHA256, keyed with the webhook's secret, of the
    timestamp, a full stop and the raw request body. PayRex fills te for a
    test-mode event and li for a live one, leaving the other empty, so the
    one that is filled in is checked. Either way it only matches if it was
    made with the secret.
    """
    secret = settings.PAYREX_WEBHOOK_SECRET
    if not secret or not header:
        return False
    parts = dict(p.strip().split("=", 1) for p in header.split(",") if "=" in p)
    timestamp = parts.get("t", "")
    first, second = ("li", "te") if live() else ("te", "li")
    supplied = parts.get(first) or parts.get(second) or ""
    if not timestamp or not supplied:
        return False
    signed = timestamp.encode() + b"." + body
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, supplied)


def sign(body, timestamp="1700000000"):
    """Make a header the way PayRex does. Used by the tests and by the
    simulate_payment command for trying the flow without a real payment."""
    digest = hmac.new(settings.PAYREX_WEBHOOK_SECRET.encode(),
                      timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
    return f"t={timestamp},te=,li={digest}" if live() else f"t={timestamp},te={digest},li="
