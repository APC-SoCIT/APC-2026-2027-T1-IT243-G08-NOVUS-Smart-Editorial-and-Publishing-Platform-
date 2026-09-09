from rest_framework import serializers

from apps.editorial.models import Article


class PublicArticleListSerializer(serializers.ModelSerializer):
    """Homepage / Article Listing Page wireframes — card view."""

    author_name = serializers.CharField(source="writer.get_full_name", read_only=True)

    class Meta:
        model = Article
        fields = ["id", "title", "category", "tags", "author_name", "published_at"]


class PublicArticleDetailSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source="writer.get_full_name", read_only=True)

    class Meta:
        model = Article
        fields = ["id", "title", "body", "category", "tags", "author_name", "published_at"]
