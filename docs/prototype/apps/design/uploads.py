"""
Direct-to-storage uploads.

A print-resolution magazine PDF routinely exceeds a hundred megabytes. Passing
one through the application means holding it in a process that also serves
every other request, on an instance with a fixed and modest memory budget —
which is how an upload takes the whole service down rather than merely failing.

The file therefore goes straight from the browser to object storage, and the
application never touches its bytes. It issues a signed instruction permitting
one upload to one key for a short window, then verifies afterwards that the
object arrived and is what was promised.

Two properties make this safe rather than merely convenient. The key is
generated server-side, so a client cannot choose where its file lands or
overwrite somebody else's. And the record is created only after the object is
confirmed present, so a failed or abandoned upload leaves no row claiming a
file that does not exist.
"""
import uuid
from datetime import datetime

from botocore.exceptions import ClientError
from django.conf import settings

ALLOWED_TYPES = {"application/pdf"}
MAX_BYTES = 200 * 1024 * 1024        # 200 MB
URL_TTL_SECONDS = 900                 # 15 minutes to begin and finish


class UploadError(Exception):
    """Raised with a message intended for the user."""


def _client():
    import boto3
    from botocore.config import Config

    return boto3.client(
        "s3",
        endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def build_key(issue_number, version, filename):
    """A server-chosen key.

    The client supplies only the original filename, which is used for the
    extension and nothing else. Including a random component means two
    designers uploading at the same moment cannot collide, and a client
    cannot target an existing object by guessing its path.
    """
    stamp = datetime.utcnow().strftime("%Y/%m")
    token = uuid.uuid4().hex[:12]
    safe = "".join(c for c in filename if c.isalnum() or c in "._-")[-60:]
    return f"designs/{stamp}/issue-{issue_number}-{version}-{token}-{safe}"


def presign_put(key, content_type):
    """A signed instruction permitting one upload to one key.

    The content type is bound into the signature, so a client that promised a
    PDF cannot then send something else — the storage service rejects the
    mismatch before any byte is stored.
    """
    if content_type not in ALLOWED_TYPES:
        raise UploadError(
            "The edition must be a PDF. Export from InDesign before uploading; "
            "this file becomes what subscribers read and download."
        )

    return _client().generate_presigned_url(
        "put_object",
        Params={
            "Bucket": settings.R2_PRIVATE_BUCKET,
            "Key": key,
            "ContentType": content_type,
        },
        ExpiresIn=URL_TTL_SECONDS,
    )


def confirm(key, expected_type=None):
    """Verify the object arrived before any record is created.

    Returns its size in bytes. A client reporting success is not evidence that
    the upload happened; the storage service is.
    """
    try:
        head = _client().head_object(
            Bucket=settings.R2_PRIVATE_BUCKET, Key=key)
    except ClientError:
        raise UploadError(
            "The upload did not complete. Nothing was saved — please try again."
        )

    size = head.get("ContentLength", 0)
    if size == 0:
        raise UploadError("The uploaded file is empty.")
    if size > MAX_BYTES:
        raise UploadError(
            f"The edition exceeds the {MAX_BYTES // (1024 * 1024)} MB limit."
        )

    if expected_type and head.get("ContentType") != expected_type:
        raise UploadError("The uploaded file is not the type that was declared.")

    return size
