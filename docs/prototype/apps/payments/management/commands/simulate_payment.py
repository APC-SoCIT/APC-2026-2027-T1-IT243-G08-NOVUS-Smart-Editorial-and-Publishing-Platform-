"""
Play out a paid checkout without paying, for trying the flow or a demo when
PayRex cannot be reached. Test keys only.

    python manage.py simulate_payment reader@boss.ph MONTHLY

The notification goes to the real webhook handler with a real signature,
so it passes every check a PayRex notification would.
"""
import json
import secrets
import time

from django.core.management.base import BaseCommand, CommandError
from django.test import RequestFactory

from apps.accounts.models import User
from apps.payments import payrex
from apps.payments.plans import PLANS


def paid_event(reader, plan, reference, pay_id=None, amount=None, status="succeeded",
               method="gcash"):
    """A payment_intent.succeeded event shaped like PayRex's."""
    now = int(time.time())
    amount = plan.amount if amount is None else amount
    return {
        "id": f"evt_{secrets.token_hex(8)}", "resource": "event",
        "type": payrex.PAID_EVENT, "livemode": False, "pending_webhooks": 1,
        "data": {"resource": {
            "id": pay_id or f"pi_{secrets.token_hex(8)}", "resource": "payment_intent",
            "amount": amount, "amount_received": amount if status == "succeeded" else 0,
            "currency": "PHP", "status": status, "livemode": False,
            "description": f"BOSS Magazine {plan.name} subscription ({reference})",
            "metadata": {"reader_id": str(reader.pk), "plan": plan.code, "reference": reference},
            "payment_method_id": f"pm_{secrets.token_hex(6)}",
            "payment_methods": [method],
            "created_at": now, "updated_at": now,
        }, "previous_attributes": {"status": "awaiting_next_action"}},
        "created_at": now, "updated_at": now,
    }


class Command(BaseCommand):
    help = "Simulate a paid PayRex checkout (test keys only)."

    def add_arguments(self, parser):
        parser.add_argument("email")
        parser.add_argument("plan", choices=list(PLANS))

    def handle(self, email, plan, **options):
        if payrex.live():
            raise CommandError("Refused: PayRex is in live mode.")
        if not payrex.signature_ok(payrex.sign(b"x"), b"x"):
            raise CommandError("Set PAYREX_WEBHOOK_SECRET first.")
        reader = User.objects.filter(email=email, role=User.Role.READER).first()
        if reader is None:
            raise CommandError(f"No reader with the address {email}.")
        from apps.payments.services import new_reference
        from apps.payments.views import PaymentWebhookView
        body = json.dumps(paid_event(reader, PLANS[plan], new_reference(reader))).encode()
        request = RequestFactory().post("/api/payments/webhook/", body,
                                        content_type="application/json",
                                        HTTP_PAYREX_SIGNATURE=payrex.sign(body))
        r = PaymentWebhookView.as_view()(request)
        self.stdout.write(f"{r.status_code} {r.content.decode()}")
