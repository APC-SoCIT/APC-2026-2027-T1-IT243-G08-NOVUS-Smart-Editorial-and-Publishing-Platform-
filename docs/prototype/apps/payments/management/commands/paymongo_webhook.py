"""
Register NOVUS with PayMongo so it is told about payments.

    python manage.py paymongo_webhook https://<backend>/api/payments/webhook/

Prints the secret PayMongo will sign notifications with. Put it in the
PAYMONGO_WEBHOOK_SECRET setting on the server. (The same can be done in the
PayMongo dashboard under Developers, then Webhooks.)
"""
from django.core.management.base import BaseCommand, CommandError

from apps.payments import paymongo

EVENTS = ["checkout_session.payment.paid"]


class Command(BaseCommand):
    help = "Register the payment notification address with PayMongo."

    def add_arguments(self, parser):
        parser.add_argument("url")

    def handle(self, url, **options):
        from django.conf import settings
        if not settings.PAYMONGO_SECRET_KEY:
            raise CommandError("Set PAYMONGO_SECRET_KEY first.")
        if not url.startswith("https://") or not url.rstrip("/").endswith("/api/payments/webhook"):
            raise CommandError("The address should be https://<backend>/api/payments/webhook/")
        try:
            webhook_id, secret = paymongo.create_webhook(url, EVENTS)
        except paymongo.PayMongoError as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"Registered {webhook_id} for {', '.join(EVENTS)}")
        self.stdout.write(f"PAYMONGO_WEBHOOK_SECRET={secret}")
