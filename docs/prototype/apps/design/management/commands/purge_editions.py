"""
Reclaim storage held by editions nothing will read again.

    python manage.py purge_editions --dry-run     # report only
    python manage.py purge_editions               # act
    python manage.py purge_editions --orphans     # include abandoned uploads

Superseded editions are removed automatically when an issue publishes. This
command exists for issues published before that behaviour, and for the
abandoned uploads nothing else knows about.
"""
from django.core.management.base import BaseCommand

from apps.design.retention import (
    find_orphaned_objects, human_bytes, purge_superseded_editions,
)
from apps.issues.models import Issue


class Command(BaseCommand):
    help = "Remove edition files that are no longer needed."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true",
                            help="Report what would be removed, and remove nothing.")
        parser.add_argument("--orphans", action="store_true",
                            help="Also remove uploads no record refers to.")
        parser.add_argument("--min-age-days", type=int, default=7,
                            help="Leave orphans newer than this, in case an "
                                 "upload is still in progress.")

    def handle(self, *args, **o):
        dry = o["dry_run"]
        if dry:
            self.stdout.write(self.style.WARNING("Dry run — nothing will be removed.\n"))

        total, freed = 0, 0
        for issue in Issue.objects.filter(
                status__in=[Issue.Status.PUBLISHED, Issue.Status.ARCHIVED]):
            n, b = purge_superseded_editions(issue, dry_run=dry)
            if n:
                self.stdout.write(
                    f"  Issue {issue.number}: {n} superseded edition(s), "
                    f"{human_bytes(b)}")
                total, freed = total + n, freed + b

        self.stdout.write(self.style.SUCCESS(
            f"\n{total} superseded edition(s), {human_bytes(freed)}"))

        if not o["orphans"]:
            return

        from datetime import timedelta

        from django.utils import timezone

        cutoff = timezone.now() - timedelta(days=o["min_age_days"])
        orphans = [x for x in find_orphaned_objects() if x[2] < cutoff]

        if not orphans:
            self.stdout.write("\nNo abandoned uploads.")
            return

        obytes = sum(size for _, size, _ in orphans)
        self.stdout.write(f"\n{len(orphans)} abandoned upload(s), "
                          f"{human_bytes(obytes)}")
        for key, size, _ in orphans[:10]:
            self.stdout.write(f"  {human_bytes(size):>10}  {key}")
        if len(orphans) > 10:
            self.stdout.write(f"  … and {len(orphans) - 10} more")

        if dry:
            return

        from django.conf import settings

        from apps.design.uploads import _client

        client = _client()
        for key, _, _ in orphans:
            client.delete_object(Bucket=settings.R2_PRIVATE_BUCKET, Key=key)
        self.stdout.write(self.style.SUCCESS(
            f"Removed {len(orphans)} abandoned upload(s), {human_bytes(obytes)}"))
