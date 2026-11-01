from django.urls import path

from apps.notifications import staff_views

app_name = "notifications"

urlpatterns = [
    path("sms/<int:log_id>/status/", staff_views.sms_check_status, name="sms_status"),
    path("sms/<int:log_id>/retry/", staff_views.sms_retry, name="sms_retry"),
]
