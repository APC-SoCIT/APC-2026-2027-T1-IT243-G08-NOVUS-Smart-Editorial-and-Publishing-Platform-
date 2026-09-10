from django.utils import timezone
from rest_framework import serializers

from .models import Issue


class IssueListSerializer(serializers.ModelSerializer):
    total_articles = serializers.IntegerField(read_only=True)
    approved_articles = serializers.IntegerField(read_only=True)
    is_ready = serializers.BooleanField(read_only=True)
    has_approved_design = serializers.SerializerMethodField()

    class Meta:
        model = Issue
        fields = [
            "id", "number", "title", "target_release_date", "cover_image",
            "status", "scheduled_for", "published_at",
            "total_articles", "approved_articles", "is_ready",
            "has_approved_design", "created_at",
        ]
        read_only_fields = ["id", "status", "scheduled_for", "published_at", "created_at"]

    def get_has_approved_design(self, obj):
        return obj.approved_design is not None


class IssueDetailSerializer(IssueListSerializer):
    articles = serializers.SerializerMethodField()
    blocking_reasons = serializers.SerializerMethodField()
    design = serializers.SerializerMethodField()

    class Meta(IssueListSerializer.Meta):
        fields = IssueListSerializer.Meta.fields + [
            "articles", "blocking_reasons", "design",
        ]

    def get_articles(self, obj):
        from apps.editorial.serializers import ArticleListSerializer
        return ArticleListSerializer(
            obj.articles.order_by("issue_order", "id"), many=True
        ).data

    def get_blocking_reasons(self, obj):
        return obj.blocking_reasons()

    def get_design(self, obj):
        from apps.design.serializers import MagazineDesignSerializer
        d = obj.approved_design
        return MagazineDesignSerializer(d).data if d else None


class ScheduleSerializer(serializers.Serializer):
    """UC-2.4 Schedule Issue Release."""

    scheduled_for = serializers.DateTimeField()

    def validate_scheduled_for(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError("The release time must be in the future.")
        return value
