"""Public views for home/about/contact/faq plus error handlers."""
from django.shortcuts import render

from apps.brands.models import Brand
from apps.content.models import (
    AboutPageContent,
    Article,
    ContactPageContent,
    FAQ,
    HeroShowcase,
    HomePageContent,
)
from apps.services.models import Service


def home(request):
    return render(
        request,
        "home.html",
        {
            "home_content": HomePageContent.objects.first(),
            "hero_showcase": HeroShowcase.load(),
            "services": Service.objects.filter(active=True)[:6],
            # Brands belong to services; the homepage strip shows the ones
            # the business is known for (its first/primary services' brands).
            "brands": Brand.objects.filter(active=True, service__active=True).select_related("service"),
            # Logo carousel needs actual logo files; filter by non-empty image.
            "brands_with_logo": (
                Brand.objects.filter(active=True, service__active=True)
                .exclude(image="")
                .select_related("service")
            ),
            "latest_articles": Article.objects.filter(published=True).select_related("service")[:3],
            "faqs": FAQ.objects.filter(active=True)[:6],
        },
    )


def about(request):
    return render(
        request,
        "about.html",
        {"about_content": AboutPageContent.objects.first()},
    )


def contact(request):
    return render(
        request,
        "contact.html",
        {"contact_content": ContactPageContent.objects.first()},
    )


def faq(request):
    return render(
        request,
        "faq.html",
        {"faqs": FAQ.objects.filter(active=True)},
    )


def error_400(request, exception=None):
    return render(request, "400.html", status=400)


def error_403(request, exception=None):
    return render(request, "403.html", status=403)


def error_404(request, exception=None):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)
