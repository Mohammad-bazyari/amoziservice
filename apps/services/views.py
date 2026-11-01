"""Public service pages."""
from django.shortcuts import get_object_or_404, render

from apps.content.models import Service, ServiceArea


def service_list(request):
    qs = Service.objects.filter(active=True).prefetch_related("areas")
    detected_area = (request.GET.get("city") or "").strip()
    if detected_area:
        # Smart filter: a visitor coming from a regional campaign/link sees the
        # service cards that actually have a landing page for their city first.
        qs = sorted(
            qs,
            key=lambda s: (
                not s.areas.filter(active=True, area__iexact=detected_area).exists(),
                s.sort_order,
            ),
        )
    return render(
        request,
        "services/list.html",
        {"services": qs, "detected_area": detected_area},
    )


def service_detail(request, slug):
    service = get_object_or_404(Service, slug=slug, active=True)
    # Brands belong to the service: show only this service's own brands.
    return render(
        request,
        "services/detail.html",
        {
            "service": service,
            "brands": service.brands.filter(active=True),
            "band_service": service,
        },
    )


def area_detail(request, slug):
    area = get_object_or_404(
        ServiceArea.objects.select_related("service"), slug=slug, active=True
    )
    service = area.service
    return render(
        request,
        "services/area.html",
        {
            "area": area,
            "service": service,
            "brands": service.brands.filter(active=True),
            "other_areas": service.areas.filter(active=True).exclude(pk=area.pk)[:6],
            # Preselect this service + carry the area into the request flow.
            "band_service": service,
            "request_url": f"/request/?service={service.pk}&area={area.area}",
            "page_name": area.h1,
            "page_description": area.meta_description
            or (area.intro or f"{area.h1} با ثبت درخواست آنلاین و تماس سریع تعمیرکار."),
            "page_type": "Service",
        },
    )
