"""
Register NOVUS with PayRex so it is told about payments.

    python manage.py payrex_webhook https://<backend>/api/payments/webhook/

Prints the secret PayRex will sign notifications with. Put it in the
PAYREX_WEBHOOK_SECRET setting on the server. (The same can be done in the
PayRex dashboard under Developers, then Webhooks.)
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.payments import payrex


class Command(BaseCommand):
    help = "Register the payment notification address with PayRex."

    def add_arguments(self, parser):
        parser.add_argument("url")

    def handle(self, url, **options):
        if not settings.PAYREX_SECRET_KEY:
            raise CommandError("Set PAYREX_SECRET_KEY first.")
        if not url.startswith("https://") or not url.rstrip("/").endswith("/api/payments/webhook"):
            raise CommandError("The address should be https://<backend>/api/payments/webhook/")
        try:
            webhook_id, secret = payrex.create_webhook(url, [payrex.PAID_EVENT])
        except payrex.PayRexError as exc:
            raise CommandError(str(exc))
        self.stdout.write(f"Registered {webhook_id} for {payrex.PAID_EVENT}")
        self.stdout.write(f"PAYREX_WEBHOOK_SECRET={secret}")
