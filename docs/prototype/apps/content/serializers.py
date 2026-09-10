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
