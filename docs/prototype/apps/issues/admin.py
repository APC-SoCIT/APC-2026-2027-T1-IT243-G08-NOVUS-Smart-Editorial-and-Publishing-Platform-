from django.contrib import admin

from .models import Issue


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ["number", "title", "status", "target_release_date", "published_at"]
    list_filter = ["status"]
