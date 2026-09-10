from rest_framework import serializers


class RelativeImageField(serializers.ImageField):
    """Returns "/media/..." instead of an absolute backend URL, so the
    image resolves through whichever origin serves the frontend."""

    def to_representation(self, value):
        return value.url if value else None

from apps.editorial.models import Article


class PublicArticleListSerializer(serializers.ModelSerializer):
    """Homepage / Article Listing Page wireframes — card view."""

    author_name = serializers.CharField(source="writer.get_full_name", read_only=True)
    reading_time = serializers.IntegerField(read_only=True)

    hero_image = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = ["id", "slug", "title", "excerpt", "category", "tags",
                  "hero_image", "author_name", "reading_time",
                  "is_featured", "is_premium", "published_at"]


class PublicArticleDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="writer.get_full_name", read_only=True)
    reading_time = serializers.IntegerField(read_only=True)
    is_locked = serializers.SerializerMethodField()
    images = serializers.SerializerMethodField()

    def _has_access(self):
        """UC-8.2 Access Premium Articles. Staff always read their own
        publication; readers need an active subscription."""
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.role != user.Role.READER:
            return True
        profile = getattr(user, "reader_profile", None)
        return bool(profile and profile.tier == profile.Tier.SUBSCRIBER)

    def get_is_locked(self, obj):
        return obj.is_premium and not self._has_access()

    def get_images(self, obj):
        from apps.editorial.serializers import ArticleImageSerializer
        return ArticleImageSerializer(obj.images.all(), many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if data.get('is_locked'):
            # Show the opening rather than nothing — the extract is what
            # sells the subscription.
            from django.utils.html import strip_tags
            text = strip_tags(instance.body or '')
            data['body'] = f'<p>{text[:450]}…</p>'
            data['images'] = []
        return data

    hero_image = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = ["id", "slug", "title", "excerpt", "body", "category", "tags",
                  "hero_image", "hero_caption", "images", "author_name",
                  "reading_time", "is_premium", "is_locked", "published_at"]


class PublicIssueListSerializer(serializers.ModelSerializer):
    """The newsstand view — UC-8.1 Download Digital Issues."""

    cover_image = RelativeImageField(required=False, allow_null=True)
    article_count = serializers.SerializerMethodField()

    class Meta:
        from apps.issues.models import Issue
        model = Issue
        fields = ["id", "number", "title", "cover_image",
                  "article_count", "published_at"]

    def get_article_count(self, obj):
        return obj.articles.count()


class PublicIssueDetailSerializer(PublicIssueListSerializer):
    articles = serializers.SerializerMethodField()
    replica_url = serializers.SerializerMethodField()
    replica_available = serializers.BooleanField(read_only=True)
    can_access = serializers.SerializerMethodField()

    class Meta(PublicIssueListSerializer.Meta):
        fields = PublicIssueListSerializer.Meta.fields + [
            "articles", "replica_url", "replica_available", "can_access",
        ]

    def _is_subscriber(self):
        request = self.context.get("request")
        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return False
        if user.role != user.Role.READER:
            return True
        profile = getattr(user, "reader_profile", None)
        return bool(profile and profile.tier == profile.Tier.SUBSCRIBER)

    def get_can_access(self, obj):
        return self._is_subscriber()

    def get_articles(self, obj):
        return PublicArticleListSerializer(
            obj.articles.filter(status="PUBLISHED").order_by("issue_order", "id"),
            many=True, context=self.context,
        ).data

    def get_replica_url(self, obj):
        """The PDF is withheld entirely from non-subscribers — unlike article
        text, there is no partial version of a magazine file."""
        if not self._is_subscriber():
            return None
        design = obj.approved_design
        return design.file.url if design and design.file else None
