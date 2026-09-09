from django.contrib import admin

from .models import ArticleEvaluation


@admin.register(ArticleEvaluation)
class ArticleEvaluationAdmin(admin.ModelAdmin):
    list_display = [
        "article", "overall_score", "recommendation",
        "is_overridden", "created_at",
    ]
    list_filter = ["recommendation", "is_overridden"]
    readonly_fields = ["raw_response", "created_at", "updated_at"]
