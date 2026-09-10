from rest_framework import serializers

from apps.editorial.models import Article


class PublicArticleListSerializer(serializers.ModelSerializer):
    """Homepage / Article Listing Page wireframes — card view."""

    author_name = serializers.CharField(source="writer.get_full_name", read_only=True)
    reading_time = serializers.IntegerField(read_only=True)

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

    class Meta:
        model = Article
        fields = ["id", "slug", "title", "excerpt", "body", "category", "tags",
                  "hero_image", "hero_caption", "images", "author_name",
                  "reading_time", "published_at"]
