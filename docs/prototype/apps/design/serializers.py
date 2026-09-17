from rest_framework import serializers


class RelativeImageField(serializers.ImageField):
    """Relative URLs so images resolve through whichever origin serves
    the frontend."""

    def to_representation(self, value):
        if not value:
            return None
        # With object storage the URL is already absolute and points at
        # the CDN. Only the local-disk fallback needs the relative form.
        return value.url

from .models import MagazineDesign

# PDF_ONLY: the layout becomes the subscriber edition, read in the browser
# and downloaded. A working file cannot be either, so accepting one would
# mean approving a layout that can never ship.
ALLOWED_EXT = {".pdf"}
COVER_EXT = {".png", ".jpg", ".jpeg", ".webp"}
# 25 MB. The wireframe said 100, but the hosting tier has 512 MB of memory
# in total and an upload that size is handled in the same process that
# serves every other request. A print-resolution issue PDF exceeding this
# should be delivered as a compressed export.
# Applies to the cover image and to legacy multipart submissions. The
# edition itself never passes through this process — see uploads.py, which
# enforces its ceiling against the object in storage.
MAX_BYTES = 25 * 1024 * 1024


class MagazineDesignSerializer(serializers.ModelSerializer):
    designer_name = serializers.CharField(source="designer.get_full_name", read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()
    issue_title = serializers.SerializerMethodField()
    cover_image = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = MagazineDesign
        fields = [
            "id", "issue", "issue_title", "version", "file", "file_name",
            "cover_image", "designer", "designer_name", "notes_to_editor", "status",
            "reviewed_by", "reviewer_name", "reviewed_at", "revision_notes",
            "created_at",
        ]
        read_only_fields = [
            "id", "designer", "designer_name", "status", "reviewed_by",
            "reviewer_name", "reviewed_at", "revision_notes", "created_at",
        ]

    def get_reviewer_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else None

    def get_issue_title(self, obj):
        return f"Issue #{obj.issue.number} — {obj.issue.title}"

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None

    def validate_file(self, value):
        """UC-1.12 E2: reject unsupported types and oversized files before upload."""
        name = value.name.lower()
        if not any(name.endswith(e) for e in ALLOWED_EXT):
            raise serializers.ValidationError(
                "The layout must be a PDF. Export from InDesign before uploading — "
                "the file becomes the edition subscribers read and download."
            )
        if value.size > MAX_BYTES:
            raise serializers.ValidationError(
                "File exceeds the 25 MB limit. Export the PDF at "
                "screen resolution rather than print resolution."
            )
        return value

    def validate_cover_image(self, value):
        if value and not any(value.name.lower().endswith(e) for e in COVER_EXT):
            raise serializers.ValidationError(
                f"The cover must be an image ({', '.join(sorted(COVER_EXT))})."
            )
        return value

    def validate(self, attrs):
        """A first version needs a cover: it is what readers see in the archive,
        and an issue published without one shows an empty rectangle."""
        # The edition arrives by reference under the direct-upload path,
        # so only the cover is validated here.
        if not self.instance and not attrs.get("cover_image"):
            existing = MagazineDesign.objects.filter(
                issue=attrs.get("issue")
            ).exclude(cover_image="").exists()
            if not existing:
                raise serializers.ValidationError({
                    "cover_image": "Upload a cover image with the first layout "
                                   "for this issue."
                })
        return attrs

    def create(self, validated_data):
        validated_data["designer"] = self.context["request"].user
        return super().create(validated_data)


class DesignRevisionSerializer(serializers.Serializer):
    """UC-1.14 Request Design Revision."""
    notes = serializers.CharField(max_length=1000, min_length=5)
