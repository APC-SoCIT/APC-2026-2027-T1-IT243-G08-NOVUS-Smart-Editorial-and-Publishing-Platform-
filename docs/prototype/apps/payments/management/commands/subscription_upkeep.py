"""
Ends subscriptions on their paid-up date and sends renewal reminders.
Runs with the daily sweep (POST /api/scheduler/check-deadlines/), or by hand:

    python manage.py subscription_upkeep
"""
from django.core.management.base import BaseCommand

from apps.payments.manage import upkeep


class Command(BaseCommand):
    help = "End lapsed subscriptions and remind readers whose access ends soon."

    def handle(self, *args, **options):
        ended, reminded = upkeep()
        self.stdout.write(f"Subscriptions ended: {ended}; renewal reminders sent: {reminded}")
