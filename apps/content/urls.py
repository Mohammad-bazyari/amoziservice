from django.urls import path, re_path

from apps.content import views

app_name = "content"

urlpatterns = [
    path("faq/", views.faq, name="faq"),
    path("articles/", views.article_list, name="articles"),
    # Unicode-aware so Persian slugs (auto-generated from Persian titles) match.
    re_path(r"^articles/(?P<slug>[^/]+)/$", views.article_detail, name="article_detail"),
    re_path(r"^p/(?P<slug>[^/]+)/$", views.page_detail, name="page"),
]
