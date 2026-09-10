from rest_framework import serializers

from .models import Article, RevisionNote


class RevisionNoteSerializer(serializers.ModelSerializer):
    editor_name = serializers.SerializerMethodField()

    class Meta:
        model = RevisionNote
        fields = [
            "id", "article", "editor", "editor_name", "section",
            "note_type", "instruction", "priority", "created_at",
        ]
        read_only_fields = ["id", "editor", "editor_name", "created_at"]

    def get_editor_name(self, obj):
        """Null editor means the note came from the AI gate, not a person."""
        return obj.editor.get_full_name() if obj.editor else None


class AssignArticleSerializer(serializers.ModelSerializer):
    """UC-1.1 Assign Article — an Editor creates the record and hands it to a
    Writer with a topic, angle, and deadline."""

    class Meta:
        model = Article
        fields = ["id", "title", "brief", "category", "writer", "deadline"]

    def validate_writer(self, value):
        if value.role != value.Role.WRITER:
            raise serializers.ValidationError("Articles can only be assigned to a Writer.")
        return value

    def create(self, validated_data):
        validated_data["assigned_by"] = self.context["request"].user
        validated_data["status"] = Article.Status.ASSIGNED
        return super().create(validated_data)


class WithdrawSerializer(serializers.Serializer):
    """UC-1.10 Withdraw Article."""
    reason = serializers.CharField(max_length=255, min_length=5)


class ArticleListSerializer(serializers.ModelSerializer):
    """Slim shape for dashboard/list views (Writer Dashboard, Editor
    Dashboard 'Pending Reviews' widget)."""

    writer_name = serializers.CharField(source="writer.get_full_name", read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_to_deadline = serializers.IntegerField(read_only=True, allow_null=True)
    latest_score = serializers.SerializerMethodField()

    class Meta:
        model = Article
        fields = [
            "id", "title", "status", "category", "writer", "writer_name",
            "editor", "latest_score", "returned_by_ai", "issue",
            "deadline", "is_overdue", "days_to_deadline", "brief",
            "created_at", "updated_at",
        ]

    def get_latest_score(self, obj):
        latest = obj.evaluations.order_by("-created_at").first()
        return latest.overall_score if latest else None


class ArticleDetailSerializer(serializers.ModelSerializer):
    revision_notes = RevisionNoteSerializer(many=True, read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_to_deadline = serializers.IntegerField(read_only=True, allow_null=True)
    latest_evaluation = serializers.SerializerMethodField()
    writer_name = serializers.CharField(source="writer.get_full_name", read_only=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "body", "category", "tags", "status",
            "writer", "writer_name", "editor", "published_at",
            "withdrawal_reason", "returned_by_ai", "issue",
            "deadline", "is_overdue", "days_to_deadline", "brief",
            "assigned_by", "revision_notes",
            "latest_evaluation",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "writer", "editor", "published_at",
            "withdrawal_reason", "returned_by_ai", "created_at", "updated_at",
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
