"""
Raises deadline notifications. Run daily:

    python manage.py check_deadlines

Missed deadlines are the operational problem NOVUS exists to solve, so this is
the command that makes the system act rather than merely record.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.editorial.models import Article
from apps.notifications.models import Notification
from apps.notifications.services import notify


class Command(BaseCommand):
    help = "Notify writers and editors about approaching and passed deadlines."

    def handle(self, *args, **options):
        today = timezone.now().date()
        soon = today + timedelta(days=2)

        open_statuses = [
            Article.Status.ASSIGNED,
            Article.Status.DRAFTING,
            Article.Status.REVISION_REQUESTED,
        ]

        near = Article.objects.filter(
            status__in=open_statuses, deadline__gt=today, deadline__lte=soon
        )
        passed = Article.objects.filter(
            status__in=open_statuses, deadline__lt=today
        )

        raised = 0
        for a in near:
            days = (a.deadline - today).days
            raised += bool(notify(
                a.writer, Notification.Kind.DEADLINE_NEAR,
                f'"{a.title}" is due in {days} day{"s" if days != 1 else ""}.',
                f"/writer/compose/{a.id}",
            ))

        for a in passed:
            over = (today - a.deadline).days
            raised += bool(notify(
                a.writer, Notification.Kind.DEADLINE_PASSED,
                f'"{a.title}" is {over} day{"s" if over != 1 else ""} overdue.',
                f"/writer/compose/{a.id}",
            ))
            raised += bool(notify(
                a.assigned_by, Notification.Kind.DEADLINE_PASSED,
                f'"{a.title}" by {a.writer.get_full_name()} is overdue.',
                f"/editor/review/{a.id}",
            ))

        self.stdout.write(self.style.SUCCESS(
            f"{near.count()} approaching, {passed.count()} overdue, "
            f"{raised} notifications raised."
        ))
