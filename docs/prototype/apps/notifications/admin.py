from django.contrib import admin

from .models import EmailDispatch, Notification, NotificationPreference


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["recipient", "kind", "message", "is_read", "created_at"]
    list_filter = ["kind", "is_read"]


admin.site.register(NotificationPreference)


@admin.register(EmailDispatch)
class EmailDispatchAdmin(admin.ModelAdmin):
    """Read-only record of every email sent, to check delivery problems."""

    list_display = ["to_address", "template", "status", "attempts", "queued_at", "sent_at"]
    list_filter = ["status", "template"]
    search_fields = ["to_address", "subject"]
    readonly_fields = [f.name for f in EmailDispatch._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
