from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

User = get_user_model()


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "username",
        "email",
        "account_type",
        "is_approved",
        "is_staff",
        "is_superuser",
        "is_active",
        "last_login",
        "date_joined",
    )
    list_display_links = ("username",)
    list_filter = ("account_type", "is_approved", "is_staff", "is_superuser", "is_active")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    actions = ["approve_users", "disapprove_users"]
    list_editable = ("account_type", "is_approved")
    readonly_fields = ("last_login", "date_joined")

    fieldsets = (
        (
            None,
            {
                "fields": ("username", "password"),
            },
        ),
        (
            _("Personal info"),
            {
                "fields": ("first_name", "last_name", "email"),
            },
        ),
        (
            _("Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            _("Important dates"),
            {
                "fields": ("last_login", "date_joined"),
            },
        ),
        (
            _("Account"),
            {
                "fields": ("account_type", "is_approved"),
            },
        ),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "email",
                    "password1",
                    "password2",
                    "account_type",
                    "is_approved",
                ),
            },
        ),
    )

    @admin.action(description="Chấp thuận người dùng đã chọn")
    def approve_users(self, request, queryset):
        queryset.update(is_approved=True)

    @admin.action(description="Bỏ chấp thuận người dùng đã chọn")
    def disapprove_users(self, request, queryset):
        queryset.update(is_approved=False)
