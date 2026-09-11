from django.contrib import admin

from .models import PlatformSetting


@admin.register(PlatformSetting)
class PlatformSettingAdmin(admin.ModelAdmin):
    list_display = ["site_name", "maintenance_mode", "updated_at"]

    fieldsets = (
        ("Site", {"fields": ("site_name", "tagline", "accent_colour",
                             "articles_per_page")}),
        ("Maintenance", {
            "fields": ("maintenance_mode", "maintenance_message"),
            "description": "While maintenance is on, the public site is held "
                           "but staff can continue working.",
        }),
    )

    def has_add_permission(self, request):
        # Single row only.
        return not PlatformSetting.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
