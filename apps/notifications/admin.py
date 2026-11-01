"""Admin for SMS logs and templates (Persian)."""
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

from apps.core.admin_toolbar import ToolbarMixin
from apps.notifications.models import SmsLog, SmsTemplate
from apps.notifications.services import kavenegar
from apps.notifications.services.dispatcher import attempt_sms_retry


@admin.register(SmsLog)
class SmsLogAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = (
        "recipient",
        "request_link",
        "status_badge",
        "provider",
        "message_id",
        "created_at",
    )
    list_filter = ("status", "provider", "created_at")
    search_fields = ("recipient", "message", "message_id")
    ordering = ("-created_at",)
    actions = ["retry_selected", "refresh_status_selected"]
    readonly_fields = (
        "request",
        "recipient",
        "sender",
        "message",
        "provider",
        "message_id",
        "status",
        "status_text",
        "response_data",
        "error_message",
        "created_by",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        ("پیامک", {"fields": ("recipient", "sender", "message", "provider")}),
        ("نتیجه", {"fields": ("status", "status_text", "message_id", "error_message", "response_data")}),
        ("ارتباط", {"fields": ("request", "created_by")}),
        ("زمان‌ها", {"fields": ("created_at", "updated_at")}),
    )

    @admin.display(description="درخواست")
    def request_link(self, obj):
        if obj.request:
            url = reverse("admin:requests_servicerequest_change", args=[obj.request_id])
            return format_html('<a href="{}">{}</a>', url, obj.request.tracking_code)
        return "—"

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        colors = {"sent": "#16a34a", "failed": "#dc2626", "pending": "#d97706"}
        return format_html(
            '<span style="background:{};color:#fff;padding:2px 10px;border-radius:999px;font-size:12px">{}</span>',
            colors.get(obj.status, "#64748b"),
            obj.get_status_display(),
        )

    @admin.action(description="تلاش مجدد ارسال پیامک‌های انتخاب‌شده")
    def retry_selected(self, request, queryset):
        ok = 0
        for log in queryset:
            updated = attempt_sms_retry(log, user=request.user)
            if updated.status == SmsLog.Status.SENT:
                ok += 1
        self.message_user(request, f"{ok} پیامک از {queryset.count()} با موفقیت ارسال شد.")

    @admin.action(description="استعلام وضعیت از کاوه‌نگار")
    def refresh_status_selected(self, request, queryset):
        checked = 0
        for log in queryset.filter(message_id__gt=""):
            result = kavenegar.check_sms_status(log.message_id)
            if result["ok"]:
                log.status_text = result.get("status_text", "")
                log.response_data = result.get("raw")
                log.save(update_fields=["status_text", "response_data", "updated_at"])
                checked += 1
        self.message_user(request, f"وضعیت {checked} پیامک استعلام شد.")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


@admin.register(SmsTemplate)
class SmsTemplateAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("label", "name", "updated_at")
    search_fields = ("label", "name", "body")
    fields = ("label", "name", "body")
    readonly_fields = ("name",)
