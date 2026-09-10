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
                  "is_featured", "published_at"]


class PublicArticleDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="writer.get_full_name", read_only=True)
    reading_time = serializers.IntegerField(read_only=True)
    images = serializers.SerializerMethodField()

    def get_images(self, obj):
        from apps.editorial.serializers import ArticleImageSerializer
        return ArticleImageSerializer(obj.images.all(), many=True).data

    hero_image = RelativeImageField(required=False, allow_null=True)

    class Meta:
        model = Article
        fields = ["id", "slug", "title", "excerpt", "body", "category", "tags",
                  "hero_image", "hero_caption", "images", "author_name",
                  "reading_time", "published_at"]
