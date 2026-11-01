from apps.content.models import Service, ServiceArea
from apps.core.models import SiteSettings


def site_settings(request):
    """Make the singleton SiteSettings available in every template."""
    return {"site_settings": SiteSettings.load()}


def default_service(request):
    """Primary service of the business (first active one), used by shared
    partials like the CTA band to stay service-centric everywhere."""
    return {
        "default_service": Service.objects.filter(active=True).order_by(
            "sort_order", "id"
        ).first(),
    }


def footer_areas(request):
    """Active regional landing pages for the footer's local-SEO links."""
    return {
        "footer_areas": ServiceArea.objects.filter(active=True, service__active=True)
        .select_related("service")[:5],
    }
