"""
Play out a paid checkout without paying, for trying the flow or a demo when
PayMongo cannot be reached. Test keys only.

    python manage.py simulate_payment reader@boss.ph MONTHLY

The notification goes to the real webhook handler with a real signature,
so it passes every check a PayMongo notification would.
"""
import json
import secrets
import time

from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory

from apps.accounts.models import User
from apps.payments import paymongo
from apps.payments.plans import PLANS


def paid_event(reader, plan, reference, pay_id=None, amount=None, status="paid", method="gcash"):
    """A checkout_session.payment.paid event shaped like PayMongo's."""
    now = int(time.time())
    return {"data": {"id": f"evt_{secrets.token_hex(8)}", "type": "event", "attributes": {
        "type": "checkout_session.payment.paid", "livemode": False,
        "data": {"id": f"cs_{secrets.token_hex(8)}", "type": "checkout_session", "attributes": {
            "reference_number": reference, "payment_method_used": method,
            "metadata": {"reader_id": str(reader.pk), "plan": plan.code, "reference": reference},
            "payments": [{"id": pay_id or f"pay_{secrets.token_hex(8)}", "type": "payment",
                          "attributes": {"amount": plan.amount if amount is None else amount,
                                         "currency": "PHP", "status": status, "paid_at": now,
                                         "source": {"type": method}}}],
        }},
        "created_at": now,
    }}}


class Command(BaseCommand):
    help = "Simulate a paid PayMongo checkout (test keys only)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("plan", choices=list(PLANS))

    def handle(self, email, plan, **options):
        if paymongo.live():
            raise CommandError("Refused: PayMongo is in live mode.")
        if not paymongo.signature_ok(paymongo.sign(b"x"), b"x"):
            raise CommandError("Set PAYMONGO_WEBHOOK_SECRET first.")
        reader = User.objects.filter(email=email, role=User.Role.READER).first()
        if reader is None:
            raise CommandError(f"No reader with the address {email}.")
        from apps.payments.services import new_reference
        body = json.dumps(paid_event(reader, PLANS[plan], new_reference(reader))).encode()
        from apps.payments.views import PayMongoWebhookView
        request = RequestFactory().post("/api/payments/webhook/", body,
                                        content_type="application/json",
                                        HTTP_PAYMONGO_SIGNATURE=paymongo.sign(body))
        r = PayMongoWebhookView.as_view()(request)
        self.stdout.write(f"{r.status_code} {r.content.decode()}")
