"""
Storage retention for magazine editions.

A print-resolution edition runs to tens or hundreds of megabytes, and an issue
that went through four review rounds holds four of them. Only one is ever read
again. Keeping the rest is paying, every month, for files nobody will open.

The rule is that a version's file is needed until the issue publishes, and not
afterwards. Before publication any version might be reverted to, so deleting
early trades a real risk against a small saving. Once the issue is out, the
accepted edition is fixed and the others have served their purpose.

The record survives the file. The review history — who submitted what, when,
what the editor asked for, what changed between rounds — is metadata, and
deleting it to reclaim bytes would discard the evidence while keeping the cost.
"""
import logging

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


def purge_superseded_editions(issue, dry_run=False):
    """Remove the files of every version that did not become the edition.

    Returns (count, bytes_freed). Safe to call more than once: a version whose
    file has already gone is skipped rather than raising.
    """
    from apps.design.models import MagazineDesign

    accepted = issue.approved_design
    if accepted is None:
        # Nothing has been accepted, so nothing is superseded. Publication
        # requires an accepted edition, so this should not occur — but a guard
        # costs nothing and deleting every version because none was accepted
        # would be the worst possible failure here.
        logger.warning("Purge skipped for issue %s: no accepted edition",
                       issue.number)
        return 0, 0

    superseded = (MagazineDesign.objects
                  .filter(issue=issue, file_purged=False)
                  .exclude(pk=accepted.pk))

    count, freed = 0, 0
    for design in superseded:
        size = design.file_size or 0
        if dry_run:
            count, freed = count + 1, freed + size
            continue

        try:
            if design.file:
                design.file.delete(save=False)
        except Exception:
            # A file already gone, or a storage service momentarily
            # unavailable, must not prevent the issue from publishing. The
            # row is left unmarked so a later sweep retries it.
            logger.exception("Could not remove edition file for design %s",
                             design.pk)
            continue

        design.file_purged = True
        design.purged_at = timezone.now()
        design.save(update_fields=["file_purged", "purged_at", "updated_at"])
        count, freed = count + 1, freed + size

    if count:
        logger.info("Issue %s: removed %d superseded edition(s), %s freed",
                    issue.number, count, human_bytes(freed))
    return count, freed


def find_orphaned_objects(prefix="designs/"):
    """Objects in storage that no record refers to.

    A direct upload that is begun and abandoned leaves a file nothing in the
    application knows about. Those are the ones that accumulate silently,
    because no screen lists them and no record points at them.

    Returns a list of (key, size, last_modified).
    """
    from django.conf import settings

    from apps.design.models import MagazineDesign
    from apps.design.uploads import _client

    if not (settings.USE_R2 and settings.R2_PRIVATE_BUCKET):
        return []

    known = set(
        MagazineDesign.objects.exclude(file="").values_list("file", flat=True)
    )

    orphans = []
    paginator = _client().get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.R2_PRIVATE_BUCKET,
                                   Prefix=prefix):
        for obj in page.get("Contents", []):
            if obj["Key"] not in known:
                orphans.append((obj["Key"], obj["Size"], obj["LastModified"]))
    return orphans


def human_bytes(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
