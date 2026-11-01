from django.urls import path, re_path

from apps.brands import views

app_name = "brands"

urlpatterns = [
    path("", views.brand_list, name="list"),
    # Unicode-aware so Persian slugs (auto-generated from Persian names) match.
    re_path(r"^(?P<slug>[^/]+)/$", views.brand_detail, name="detail"),
]
