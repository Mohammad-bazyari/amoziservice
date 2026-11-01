"""Custom Persian admin site with a stats dashboard."""
from django.contrib import admin
from django.db.models import Count
from django.utils import timezone

from apps.core.models import SiteSettings
from apps.requests.models import ServiceRequest


class BaradaranAdminSite(admin.AdminSite):
    index_title = "داشبورد مدیریت"
    site_url = "/"
    enable_nav_sidebar = True
    index_template = "admin/dashboard.html"

    def each_context(self, request):
        ctx = super().each_context(request)
        s = SiteSettings.load()
        ctx["site_header"] = f"{s.business_name} — پنل مدیریت"
        ctx["site_title"] = f"پنل مدیریت {s.business_name}"
        ctx["usta_logo"] = True
        return ctx

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(_dashboard_stats())
        return super().index(request, extra_context=extra_context)


def _dashboard_stats():
    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timezone.timedelta(days=7)
    month_start = today_start - timezone.timedelta(days=30)

    by_status = dict(
        ServiceRequest.objects.values_list("status").annotate(c=Count("id"))
    )
    status_cards = [
        {"key": key, "label": label, "count": by_status.get(key, 0)}
        for key, label in ServiceRequest.Status.choices
    ]
    recent = ServiceRequest.objects.select_related("service", "brand", "problem")[:8]
    top_brands = (
        ServiceRequest.objects.values("brand__name", "other_brand_name")
        .annotate(c=Count("id"))
        .order_by("-c")[:5]
    )
    daily = (
        ServiceRequest.objects.filter(created_at__gte=week_start)
        .values("created_at__date")
        .annotate(c=Count("id"))
        .order_by("created_at__date")
    )
    max_daily = max((row["c"] for row in daily), default=1) or 1
    return {
        "current_date": timezone.localtime(now),
        "status_cards": status_cards,
        "total_requests": ServiceRequest.objects.count(),
        "today_requests": ServiceRequest.objects.filter(created_at__gte=today_start).count(),
        "week_requests": ServiceRequest.objects.filter(created_at__gte=week_start).count(),
        "month_requests": ServiceRequest.objects.filter(created_at__gte=month_start).count(),
        "recent_requests": recent,
        "top_brands": [
            {
                "name": row["brand__name"] or row["other_brand_name"] or "سایر",
                "count": row["c"],
            }
            for row in top_brands
        ],
        "daily_counts": daily,
        "max_daily": max_daily,
    }


# Replace the default site instance (kept: /admin/ URL).
admin.site.__class__ = BaradaranAdminSite
