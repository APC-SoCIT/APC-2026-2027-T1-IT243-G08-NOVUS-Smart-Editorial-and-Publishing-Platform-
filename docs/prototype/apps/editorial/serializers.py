from rest_framework import serializers

from .models import Article, RevisionNote


class RevisionNoteSerializer(serializers.ModelSerializer):
    editor_name = serializers.CharField(source="editor.get_full_name", read_only=True)

    class Meta:
        model = RevisionNote
        fields = [
            "id", "article", "editor", "editor_name", "section",
            "note_type", "instruction", "priority", "created_at",
        ]
        read_only_fields = ["id", "editor", "editor_name", "created_at"]


class ArticleListSerializer(serializers.ModelSerializer):
    """Slim shape for dashboard/list views (Writer Dashboard, Editor
    Dashboard 'Pending Reviews' widget)."""

    writer_name = serializers.CharField(source="writer.get_full_name", read_only=True)
    latest_score = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id", "title", "status", "category", "writer", "writer_name",
            "editor", "latest_score", "created_at", "updated_at",
        ]

    def get_latest_score(self, obj):
        latest = obj.evaluations.order_by("-created_at").first()
        return latest.overall_score if latest else None


class ArticleDetailSerializer(serializers.ModelSerializer):
    revision_notes = RevisionNoteSerializer(many=True, read_only=True)
    latest_evaluation = serializers.SerializerMethodField()
    writer_name = serializers.CharField(source="writer.get_full_name", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "body", "category", "tags", "status",
            "writer", "writer_name", "editor", "published_at",
            "withdrawal_reason", "revision_notes", "latest_evaluation",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "writer", "editor", "published_at",
            "withdrawal_reason", "created_at", "updated_at",
        ]

    def get_latest_evaluation(self, obj):
        """UC-1.5: the narrative brief is shown to the Editor as draft notes and
        to the Writer as read-only guidance."""
        from apps.ai_eval.serializers import ArticleEvaluationSerializer
        latest = obj.evaluations.order_by("-created_at").first()
        return ArticleEvaluationSerializer(latest).data if latest else None


class ArticleCreateSerializer(serializers.ModelSerializer):
    """UC-1.3 Verify Draft Article — Writer creates/saves a draft."""

    class Meta:
        model = Article
        fields = ["id", "title", "body", "category", "tags"]
        extra_kwargs = {
            "body": {"required": False, "allow_blank": True},
            "category": {"required": False, "allow_blank": True},
            "tags": {"required": False, "allow_blank": True},
        }

    def create(self, validated_data):
        validated_data["writer"] = self.context["request"].user
        return super().create(validated_data)


class RequestRevisionSerializer(serializers.Serializer):
    """UC-1.4 Request Revision — one or more notes in a single call, matching
    the 'Add Another Note' composer screen."""

    notes = RevisionNoteSerializer(many=True)

    def save(self, article, editor):
        created = []
        for note in self.validated_data["notes"]:
            created.append(
                RevisionNote.objects.create(article=article, editor=editor, **note)
            )
        article.status = Article.Status.REVISION_REQUESTED
        article.editor = editor
        article.save(update_fields=["status", "editor", "updated_at"])
        return created


class OverrideSerializer(serializers.Serializer):
    """UC-1.5 Verify Override AI — editor overrides the AI verdict and must
    provide a justification."""

    reason = serializers.CharField(max_length=500, min_length=10)
