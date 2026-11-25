from django.contrib import admin

from . import categories
from .models import Article, Category, RevisionNote


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


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Rename or archive a category. Archiving hides it from the pickers;
    articles already filed under it keep it."""

    list_display = ["name", "is_active", "article_count", "created_by", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    fields = ["name", "is_active"]
    actions = ["archive", "restore"]

    @admin.display(description="Articles")
    def article_count(self, obj):
        return Article.objects.filter(category=obj.name).count()

    def save_model(self, request, obj, form, change):
        if change and "name" in form.changed_data:
            new = categories.normalise(obj.name)
            obj.name = Category.objects.get(pk=obj.pk).name  # rename() moves articles
            categories.rename(obj, new)
            if "is_active" in form.changed_data:
                obj.save(update_fields=["is_active", "updated_at"])
            return
        if not change:
            obj.name = categories.normalise(obj.name)
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def has_delete_permission(self, request, obj=None):
        # Archive instead: deleting would orphan the articles' category.
        return False

    @admin.action(description="Archive selected categories")
    def archive(self, request, queryset):
        n = queryset.update(is_active=False)
        self.message_user(request, f"{n} categories archived.")

    @admin.action(description="Restore selected categories")
    def restore(self, request, queryset):
        n = queryset.update(is_active=True)
        self.message_user(request, f"{n} categories restored.")

