from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.urls import include, path
from django.views.generic import TemplateView

from config.sitemaps import SITEMAPS

urlpatterns = [
    # Recovery endpoints must be included BEFORE admin.site.urls: the admin
    # site registers a catch-all for /admin/* that would shadow them.
    path("admin/", include("apps.accounts.urls")),
    path("admin/", admin.site.urls),
    path("", include("apps.core.urls")),
    path("services/", include("apps.services.urls")),
    path("brands/", include("apps.brands.urls")),
    path("request/", include("apps.requests.urls")),
    path("", include("apps.content.urls")),
    path("panel/", include("apps.notifications.urls")),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": SITEMAPS},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path(
        "robots.txt",
        TemplateView.as_view(template_name="robots.txt", content_type="text/plain"),
        name="robots",
    ),
]

# Serve uploaded media through Django in all environments. On cPanel you can
# later offload this to LiteSpeed with an .htaccess rewrite (see README).
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

handler400 = "apps.core.views.error_400"
handler403 = "apps.core.views.error_403"
handler404 = "apps.core.views.error_404"
handler500 = "apps.core.views.error_500"
