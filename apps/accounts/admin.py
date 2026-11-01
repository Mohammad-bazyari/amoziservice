from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import User
from apps.core.admin_toolbar import ToolbarMixin


@admin.register(User)
class PersianUserAdmin(ToolbarMixin, UserAdmin):
    list_display = ("username", "name_or_dash", "phone_or_dash", "is_staff", "is_active", "last_login")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "phone")
    ordering = ("-date_joined",)
    list_per_page = 25

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        ("اطلاعات شخصی", {"fields": ("first_name", "last_name", "email", "phone")}),
        (
            "دسترسی‌ها",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("تاریخ‌های مهم", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "phone", "password1", "password2"),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined")

    @admin.display(description="نام")
    def name_or_dash(self, obj):
        return obj.get_full_name() or "—"

    @admin.display(description="موبایل")
    def phone_or_dash(self, obj):
        return obj.phone or "—"
