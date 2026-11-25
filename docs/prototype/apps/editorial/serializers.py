from rest_framework import serializers


class RelativeImageField(serializers.ImageField):
    """Returns "/media/..." instead of an absolute backend URL, so the
    image resolves through whichever origin serves the frontend."""

    def to_representation(self, value):
        if not value:
            return None
        # With object storage the URL is already absolute and points at
        # the CDN. Only the local-disk fallback needs the relative form.
        return value.url

from . import categories
from .models import Article, ArticleImage, ArticleVersion, Category, RevisionNote


class ArticleImageSerializer(serializers.ModelSerializer):
    image = RelativeImageField()

    class Meta:
        model = ArticleImage
        fields = ["id", "article", "image", "caption", "created_at"]
        read_only_fields = ["id", "created_at"]


class ArticleVersionSerializer(serializers.ModelSerializer):
    submitted_by_name = serializers.CharField(
        source="submitted_by.get_full_name", read_only=True
    )
    word_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = ArticleVersion
        fields = ["id", "number", "title", "body", "excerpt",
                  "submitted_by", "submitted_by_name", "word_count", "created_at"]
        read_only_fields = fields


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


def writer_name(article):
    """The writer's name, or None for an open headline nobody has yet."""
    return article.writer.get_full_name() if article.writer_id else None


class AssignArticleSerializer(serializers.ModelSerializer):
    """UC-1.1 Assign Article — an Editor creates the record and hands it to a
    Writer with a topic, angle, and deadline. Without a writer it becomes an
    open headline in the backlog, to be given to a writer later."""

    class Meta:
        model = Article
        fields = ["id", "title", "brief", "category", "writer", "deadline"]
        extra_kwargs = {"writer": {"required": False, "allow_null": True}}

    def validate_writer(self, value):
        if value is None:
            return value
        if (value.role != value.Role.WRITER or not value.is_active
                or getattr(value, "is_suspended", False)):
            raise serializers.ValidationError("Articles can only be assigned to an active Writer.")
        return value

    def validate_category(self, value):
        return categories.clean_article_category(value)

    def create(self, validated_data):
        validated_data["assigned_by"] = self.context["request"].user
        validated_data["status"] = (Article.Status.ASSIGNED if validated_data.get("writer")
                                    else Article.Status.OPEN)
        return super().create(validated_data)


class WithdrawSerializer(serializers.Serializer):
    """UC-1.10 Withdraw Article."""
    reason = serializers.CharField(max_length=255, min_length=5)


class ArticleListSerializer(serializers.ModelSerializer):
    """Slim shape for dashboard/list views (Writer Dashboard, Editor
    Dashboard 'Pending Reviews' widget)."""

    writer_name = serializers.SerializerMethodField()
    is_overdue = serializers.BooleanField(read_only=True)
    days_to_deadline = serializers.IntegerField(read_only=True, allow_null=True)
    reading_time = serializers.IntegerField(read_only=True)
    latest_score = serializers.SerializerMethodField()
    image_count = serializers.SerializerMethodField()

    hero_image = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "status", "category", "writer", "writer_name",
            "editor", "latest_score", "returned_by_ai", "issue",
            "deadline", "is_overdue", "days_to_deadline", "brief",
            "hero_image", "excerpt", "slug", "reading_time",
            "is_featured", "image_count",
            "created_at", "updated_at",
        ]

    def get_writer_name(self, obj):
        return writer_name(obj)

    def get_latest_score(self, obj):
        latest = obj.evaluations.order_by("-created_at").first()
        return latest.overall_score if latest else None

    def get_image_count(self, obj):
        """Shown on the Designer handoff screen."""
        return obj.images.count() + (1 if obj.hero_image else 0)


class ArticleDetailSerializer(serializers.ModelSerializer):
    revision_notes = RevisionNoteSerializer(many=True, read_only=True)
    images = ArticleImageSerializer(many=True, read_only=True)
    versions = ArticleVersionSerializer(many=True, read_only=True)
    reading_time = serializers.IntegerField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    days_to_deadline = serializers.IntegerField(read_only=True, allow_null=True)
    latest_evaluation = serializers.SerializerMethodField()
    writer_name = serializers.SerializerMethodField()

    hero_image = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = [
            "id", "title", "body", "category", "tags", "status",
            "writer", "writer_name", "editor", "published_at",
            "withdrawal_reason", "returned_by_ai", "issue",
            "deadline", "is_overdue", "days_to_deadline", "brief",
            "hero_image", "hero_caption", "excerpt", "slug",
            "reading_time", "is_featured", "images",
            "assigned_by", "revision_notes", "versions", "is_premium",
            "latest_evaluation",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "status", "writer", "editor", "published_at",
            "withdrawal_reason", "returned_by_ai", "created_at", "updated_at",
        ]

    def get_writer_name(self, obj):
        return writer_name(obj)

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
        fields = ["id", "title", "body", "category", "tags",
                  "excerpt", "hero_image", "hero_caption", "is_featured"]
        extra_kwargs = {
            "body": {"required": False, "allow_blank": True},
            "category": {"required": False, "allow_blank": True},
            "tags": {"required": False, "allow_blank": True},
            "excerpt": {"required": False, "allow_blank": True},
            "hero_caption": {"required": False, "allow_blank": True},
            "hero_image": {"required": False, "allow_null": True},
            "is_featured": {"required": False},
        }

    def validate_category(self, value):
        current = self.instance.category if self.instance else ""
        return categories.clean_article_category(value, current)

    def create(self, validated_data):
        validated_data["writer"] = self.context["request"].user
        return super().create(validated_data)


class CategorySerializer(serializers.ModelSerializer):
    """The managed list behind every category picker."""

    article_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ["id", "name", "is_active", "article_count"]
        read_only_fields = ["id", "is_active", "article_count"]

    def validate_name(self, value):
        return categories.validate_new_name(value)


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
