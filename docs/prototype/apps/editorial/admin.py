from django.contrib import admin

from .models import Article, RevisionNote


class RevisionNoteInline(admin.TabularInline):
    model = RevisionNote
    extra = 0
    readonly_fields = ["created_at"]


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "writer", "editor", "status", "published_at", "updated_at"]
    list_filter = ["status", "category"]
    search_fields = ["title", "body"]
    inlines = [RevisionNoteInline]


@admin.register(RevisionNote)
class RevisionNoteAdmin(admin.ModelAdmin):
    list_display = ["article", "editor", "note_type", "priority", "created_at"]
    list_filter = ["note_type", "priority"]
