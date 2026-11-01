"""Public brand pages."""
from django.shortcuts import get_object_or_404, render

from apps.brands.models import Brand


def brand_list(request):
    return render(
        request,
        "brands/list.html",
        {"brands": Brand.objects.filter(active=True).select_related("service")},
    )


def brand_detail(request, slug):
    brand = get_object_or_404(Brand.objects.select_related("service"), slug=slug, active=True)
    # Sibling brands of the same service — a brand page is a service page.
    other_brands = brand.service.brands.filter(active=True).exclude(pk=brand.pk)
    # Troubleshooting guides of this brand's service — internal linking hub.
    related_articles = brand.service.articles.filter(published=True)[:4]
    return render(
        request,
        "brands/detail.html",
        {
            "brand": brand,
            "brand_list": other_brands,
            "band_service": brand.service,
            "related_articles": related_articles,
        },
    )
