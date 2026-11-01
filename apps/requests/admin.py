"""Admin for service requests (Persian)."""
from django.contrib import admin
from django.utils.html import format_html

from apps.content.models import Brand, ProblemOption
from apps.core.admin_toolbar import ToolbarMixin
from apps.core.templatetags.fa import fa_digits, jdate
from apps.requests.models import (
    RequestImage,
    RequestNote,
    RequestStatusHistory,
    ServiceRequest,
)


class RequestStatusHistoryInline(admin.TabularInline):
    model = RequestStatusHistory
    extra = 0
    fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    readonly_fields = ("from_status", "to_status", "changed_by", "note", "created_at")
    can_delete = False
    verbose_name = "تغییر وضعیت"
    verbose_name_plural = "تاریخچه وضعیت‌ها"

    def has_add_permission(self, request, obj=None):
        return False


class RequestNoteInline(admin.StackedInline):
    model = RequestNote
    extra = 1
    fields = ("body",)
    verbose_name = "یادداشت داخلی"
    verbose_name_plural = "یادداشت‌های داخلی"


class RequestImageInline(admin.TabularInline):
    model = RequestImage
    extra = 0
    fields = ("image", "original_filename", "size_bytes")
    readonly_fields = ("original_filename", "size_bytes")
    verbose_name = "تصویر"
    verbose_name_plural = "تصاویر مشتری"


@admin.register(ServiceRequest)
class ServiceRequestAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = (
        "tracking_code",
        "customer_name",
        "customer_phone",
        "brand_short",
        "district",
        "status_badge",
        "created_at_shamsi",
    )
    list_filter = ("status", "brand", "city", "district", "created_at")
    search_fields = ("tracking_code", "customer_name", "customer_phone", "other_brand_name")
    ordering = ("-created_at",)
    list_per_page = 25
    readonly_fields = (
        "tracking_code",
        "ip_address",
        "created_at",
        "updated_at",
        "completed_at",
    )
    inlines = [RequestImageInline, RequestStatusHistoryInline, RequestNoteInline]
    fieldsets = (
        ("وضعیت", {"fields": ("status", "tracking_code", "completed_at")}),
        ("خدمت و مشکل", {"fields": ("service", "brand", "other_brand_name", "problem", "other_problem_label", "description")}),
        ("مشتری", {"fields": ("customer_name", "customer_phone")}),
        ("آدرس", {"fields": ("province", "city", "district", "address", "plaque", "unit", "postal_code", "address_notes")}),
        ("سیستمی", {"fields": ("ip_address", "created_at", "updated_at"), "classes": ("collapse",)}),
    )
    actions = ["mark_contacted", "mark_completed", "mark_cancelled"]
    change_form_template = "admin/requests_change_form.html"

    class Media:
        js = ("js/admin-request-dependents.js",)

    def get_form(self, request, obj=None, **kwargs):
        """Relax brand/problem for the hand-add form.

        The model's clean() demands a brand or a typed brand name — right for
        the public wizard, but an operator logging a phone-in call just picks
        the service (and may not know the brand yet). The add form marks the
        instance with `_brand_optional` inside its own clean() (clean runs
        before save, so the flag must be set there); the JS filter still
        keeps the dropdowns coherent with the chosen service.
        """
        base_form = super().get_form(request, obj, **kwargs)
        if obj is not None:
            return base_form

        admin = self

        class HandAddForm(base_form):
            """Add-form variant: brand/problem optional, brand check skipped."""

            def clean(self):
                self.instance._brand_optional = True
                return super().clean()

        return HandAddForm

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """On ADD, brand/problem options come from the JS filter by service.

        The queryset starts empty (server-side) and admin-request-dependents.js
        fills it with the chosen service's rows; on CHANGE the server-side
        queryset stays full so the saved value validates without JS.
        """
        if db_field.name in ("brand", "problem"):
            # get_form receives no obj here; detect add vs change via URL kwarg
            is_add = "/add/" in request.path
            if is_add:
                kwargs["queryset"] = db_field.related_model.objects.none()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def _dependents_payload(self):
        """JSON of all brands/problems grouped by service for the JS filter."""
        import json

        payload = {
            "brands": [
                {"id": b.pk, "service": b.service_id, "label": b.name}
                for b in Brand.objects.filter(active=True).order_by("name")
            ],
            "problems": [
                {"id": p.pk, "service": p.service_id, "label": p.label}
                for p in ProblemOption.objects.filter(active=True).order_by("sort_order", "id")
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    def render_change_form(self, request, context, add=False, change=False, form_url="", obj=None):
        context["request_dependents_json"] = self._dependents_payload()
        return super().render_change_form(request, context, add=add, change=change, form_url=form_url, obj=obj)

    @admin.display(description="برند")
    def brand_short(self, obj):
        return obj.brand_display

    @admin.display(description="وضعیت")
    def status_badge(self, obj):
        return format_html(
            '<span class="admin-status-badge status-{}">{}</span>',
            obj.status,
            obj.status_label,
        )

    @admin.display(description="تاریخ ثبت", ordering="created_at")
    def created_at_shamsi(self, obj):
        date_fa = jdate(obj.created_at, "jy/jm/jd")
        time_fa = fa_digits(obj.created_at.strftime("%H:%M"))
        return f"{date_fa} - {time_fa}"

    def save_model(self, request, obj, form, change):
        """Log status changes to the history table."""
        if change and "status" in form.changed_data:
            old = type(obj).objects.get(pk=obj.pk).status
            obj._skip_status_history = False
            super().save_model(request, obj, form, change)
            if obj.status != old:
                from apps.requests.models import RequestStatusHistory

                RequestStatusHistory.objects.create(
                    request=obj,
                    from_status=old,
                    to_status=obj.status,
                    changed_by=request.user,
                    note="تغییر از پنل مدیریت",
                )
        else:
            super().save_model(request, obj, form, change)

    @admin.action(description="علامت‌گذاری: تماس گرفته شد")
    def mark_contacted(self, request, queryset):
        for obj in queryset:
            obj.set_status(ServiceRequest.Status.CONTACTED, changed_by=request.user)
        self.message_user(request, f"{queryset.count()} درخواست به‌روزرسانی شد.")

    @admin.action(description="علامت‌گذاری: تکمیل شده")
    def mark_completed(self, request, queryset):
        for obj in queryset:
            obj.set_status(ServiceRequest.Status.COMPLETED, changed_by=request.user)
        self.message_user(request, f"{queryset.count()} درخواست تکمیل شد.")

    @admin.action(description="علامت‌گذاری: لغو شده")
    def mark_cancelled(self, request, queryset):
        for obj in queryset:
            obj.set_status(ServiceRequest.Status.CANCELLED, changed_by=request.user)
        self.message_user(request, f"{queryset.count()} درخواست لغو شد.")
