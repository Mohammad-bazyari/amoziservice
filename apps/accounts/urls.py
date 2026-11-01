from django.urls import path

from apps.accounts import views

app_name = "accounts"

urlpatterns = [
    path("pw-recover/", views.recover_home, name="pw_recover"),
    path("pw-recover/start/", views.recover_start, name="pw_recover_start"),
    path("pw-recover/verify/", views.recover_verify, name="pw_recover_verify"),
    path("pw-recover/reset/", views.recover_reset, name="pw_recover_reset"),
    path(
        "pw-recover/question/",
        views.recover_question_start,
        name="pw_recover_question",
    ),
    path(
        "pw-recover/question/answer/",
        views.recover_question_verify,
        name="pw_recover_question_verify",
    ),
]
