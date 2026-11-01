from django.urls import path, re_path

from apps.services import views

app_name = "services"

urlpatterns = [
    path("", views.service_list, name="list"),
    # Unicode-aware so Persian slugs (auto-generated from Persian names) match.
    re_path(r"^(?P<slug>[^/]+)/$", views.service_detail, name="detail"),
    # Regional landing pages: /services/area/boiler-repair-karaj/ etc.
    re_path(r"^area/(?P<slug>[^/]+)/$", views.area_detail, name="area"),
]
