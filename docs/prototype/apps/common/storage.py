"""
Storage backends.

Two buckets, deliberately. Article photography is meant to be seen — it is on
the homepage, it benefits from caching, and making it public is what keeps it
fast. Magazine layouts are the product subscribers pay for, so they are never
publicly addressable; access is granted per request, after an entitlement
check, through a URL that expires.

A single public bucket would have meant the paywall controlled whether the
download link was shown rather than whether the file could be fetched — which
is not a paywall.
"""
from django.conf import settings
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible
from storages.backends.s3 import S3Storage


class PrivateMediaStorage(S3Storage):
    """Objects readable only through a signed URL.

    querystring_auth signs every generated URL; querystring_expire sets how
    long it remains valid. Fifteen minutes is long enough to start a download
    on a slow connection and short enough that a shared link is not a
    permanent licence.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("bucket_name", settings.R2_PRIVATE_BUCKET)
        kwargs.setdefault("access_key", settings.R2_ACCESS_KEY_ID)
        kwargs.setdefault("secret_key", settings.R2_SECRET_ACCESS_KEY)
        kwargs.setdefault(
            "endpoint_url",
            f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com")
        kwargs.setdefault("region_name", "auto")
        kwargs.setdefault("default_acl", None)
        kwargs.setdefault("querystring_auth", True)
        kwargs.setdefault("querystring_expire", 900)
        kwargs.setdefault("signature_version", "s3v4")
        kwargs.setdefault("file_overwrite", False)
        super().__init__(*args, **kwargs)


@deconstructible
class DeferredPrivateStorage(Storage):
    """Resolves the real backend on each call rather than at import.

    A FileField's storage is bound when the model class is defined, which
    happens before tests can override settings. Deferring the decision means
    the same field writes to R2 in production and to a temporary directory
    under test, without the test suite needing credentials or a network.
    """

    def _wrapped(self):
        if settings.USE_R2 and settings.R2_PRIVATE_BUCKET:
            return PrivateMediaStorage()
        from django.core.files.storage import default_storage
        return default_storage

    def _open(self, name, mode="rb"):
        return self._wrapped()._open(name, mode)

    def _save(self, name, content):
        return self._wrapped()._save(name, content)

    def delete(self, name):
        return self._wrapped().delete(name)

    def exists(self, name):
        return self._wrapped().exists(name)

    def listdir(self, path):
        return self._wrapped().listdir(path)

    def size(self, name):
        return self._wrapped().size(name)

    def url(self, name):
        return self._wrapped().url(name)

    def get_available_name(self, name, max_length=None):
        return self._wrapped().get_available_name(name, max_length)

    def __eq__(self, other):
        return isinstance(other, DeferredPrivateStorage)

    def __hash__(self):
        return hash(DeferredPrivateStorage)


# The model field holds this instance; it decides where to write at call time.
private_storage = DeferredPrivateStorage()
