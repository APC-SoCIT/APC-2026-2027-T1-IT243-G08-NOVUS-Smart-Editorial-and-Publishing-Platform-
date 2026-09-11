from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import ReaderProfile, User


class ReaderProfileInline(admin.StackedInline):
    """Subscription entitlement. Payment automation is Phase 2 (Module 9);
    until then an Admin grants a tier here and UC-8.2 enforces it."""
    model = ReaderProfile
    can_delete = False
    extra = 0


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Module 5: Manage User Privileges, delivered through the Django
    administration interface."""

    list_display = ["email", "get_full_name", "role", "is_active",
                    "is_suspended", "must_reset_password", "last_login"]
    list_filter = ["role", "is_active", "is_suspended", "must_reset_password"]
    search_fields = ["email", "first_name", "last_name"]
    ordering = ["last_name", "first_name"]
    inlines = [ReaderProfileInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Identity", {"fields": ("first_name", "last_name")}),
        ("Role and access", {
            "fields": ("role", "is_active", "is_suspended", "must_reset_password"),
            "description": "Suspending an account revokes access immediately "
                           "(UC-5.2.2). Their work is retained.",
        }),
        ("Permissions", {"fields": ("is_staff", "is_superuser",
                                    "groups", "user_permissions"),
                         "classes": ("collapse",)}),
        ("Dates", {"fields": ("last_login", "date_joined"), "classes": ("collapse",)}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role",
                       "password1", "password2"),
        }),
    )

    actions = ["suspend_accounts", "restore_accounts", "require_password_reset"]

    @admin.action(description="Suspend selected accounts (UC-5.2.2)")
    def suspend_accounts(self, request, queryset):
        n = queryset.exclude(pk=request.user.pk).update(
            is_suspended=True, is_active=False)
        self.message_user(request, f"{n} account(s) suspended.")

    @admin.action(description="Restore selected accounts")
    def restore_accounts(self, request, queryset):
        n = queryset.update(is_suspended=False, is_active=True)
        self.message_user(request, f"{n} account(s) restored.")

    @admin.action(description="Require a password reset (UC-5.2.3)")
    def require_password_reset(self, request, queryset):
        n = queryset.update(must_reset_password=True)
        self.message_user(request, f"{n} user(s) must reset their password.")


@admin.register(ReaderProfile)
class ReaderProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "tier", "subscription_started_at"]
    list_filter = ["tier"]
    search_fields = ["user__email"]
