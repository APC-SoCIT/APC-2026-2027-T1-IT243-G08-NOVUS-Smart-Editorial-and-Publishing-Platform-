"""Expire an account's password, to demonstrate the 90-day policy.

    python manage.py expire_password reader@boss.ph
"""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User


class Command(BaseCommand):
    help = "Backdate an account's last password change past the expiry period."

    def add_arguments(self, parser):
        parser.add_argument("email")

    def handle(self, *args, **opts):
        days = getattr(settings, "PASSWORD_EXPIRY_DAYS", 90) + 1
        n = User.objects.filter(email__iexact=opts["email"]).update(
            password_changed_at=timezone.now() - timedelta(days=days))
        if not n:
            raise CommandError(f"No account with the address {opts['email']}.")
        self.stdout.write(self.style.SUCCESS(
            f"{opts['email']}: password last changed {days} days ago. "
            f"It must be changed at the next request after signing in."))
