from rest_framework import serializers

from .models import MagazineDesign

ALLOWED_EXT = {".pdf", ".indd", ".ai", ".psd", ".png", ".jpg", ".jpeg"}
MAX_BYTES = 100 * 1024 * 1024  # 100 MB, matching the wireframe


class MagazineDesignSerializer(serializers.ModelSerializer):
    designer_name = serializers.CharField(source="designer.get_full_name", read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    file_name = serializers.SerializerMethodField()

    class Meta:
        model = MagazineDesign
        fields = [
            "id", "issue_label", "version", "file", "file_name",
            "designer", "designer_name", "notes_to_editor", "status",
            "reviewed_by", "reviewer_name", "reviewed_at", "revision_notes",
            "created_at",
        ]
        read_only_fields = [
            "id", "designer", "designer_name", "status", "reviewed_by",
            "reviewer_name", "reviewed_at", "revision_notes", "created_at",
        ]

    def get_reviewer_name(self, obj):
        return obj.reviewed_by.get_full_name() if obj.reviewed_by else None

    def get_file_name(self, obj):
        return obj.file.name.rsplit("/", 1)[-1] if obj.file else None

    def validate_file(self, value):
        """UC-1.12 E2: reject unsupported types and oversized files before upload."""
        name = value.name.lower()
        if not any(name.endswith(e) for e in ALLOWED_EXT):
            raise serializers.ValidationError(
                f"Unsupported file type. Allowed: {', '.join(sorted(ALLOWED_EXT))}"
            )
        if value.size > MAX_BYTES:
            raise serializers.ValidationError("File exceeds the 100 MB limit.")
        return value

    def create(self, validated_data):
        validated_data["designer"] = self.context["request"].user
        return super().create(validated_data)


class DesignRevisionSerializer(serializers.Serializer):
    """UC-1.14 Request Design Revision."""
    notes = serializers.CharField(max_length=1000, min_length=5)
