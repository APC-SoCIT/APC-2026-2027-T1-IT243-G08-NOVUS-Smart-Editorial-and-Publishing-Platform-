from django.contrib import admin

from .models import MagazineDesign


@admin.register(MagazineDesign)
class MagazineDesignAdmin(admin.ModelAdmin):
    list_display = ["issue_label", "version", "designer", "status", "created_at"]
    list_filter = ["status", "issue_label"]
