from django.urls import path

from apps.requests import views

app_name = "requests"

urlpatterns = [
    path("", views.start, name="start"),
    path("step/<str:step>/", views.step_view, name="step"),
    path("review/", views.review_view, name="review"),
    path("submit/", views.submit_view, name="submit"),
    path("success/<str:code>/", views.success_view, name="success"),
]
