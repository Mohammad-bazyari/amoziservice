"""SMS-based password recovery endpoints, mounted at /admin/pw-recover/.

Small JSON API consumed by the wizard embedded in the admin login page:
  1. POST start   {username}        → issues a 6-digit code via SMS
  2. POST verify  {code}            → checks the code (max 5 tries)
  3. POST reset   {new_password1,2} → sets the password and logs the user in

Every response is JSON: {"ok": bool, "stage": ..., "error": str?}
Rate limiting and attempt counting live in apps.accounts.recovery.
"""
import logging

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth import password_validation
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.accounts import recovery

logger = logging.getLogger(__name__)


@require_POST
def recover_start(request):
    username = (request.POST.get("username") or "").strip()
    user = recovery.find_recoverable_user(username)
    if user is None:
        return JsonResponse(
            {"ok": False, "error": "کاربری با این نام کاربری پیدا نشد."}, status=400
        )

    # Per-IP throttle BEFORE anything is sent: blocks SMS flooding from a
    # cookie-less attacker (the per-session cooldown alone cannot).
    if not recovery.sms_issue_allowed(request):
        return JsonResponse(
            {
                "ok": False,
                "error": "درخواست‌های مکرر؛ لطفاً چند دقیقه دیگر دوباره تلاش کنید.",
            },
            status=429,
        )

    result = recovery.issue_code(user, request)
    if not result["sent"]:
        recovery.clear(request)
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    "شماره موبایلی روی حساب شما ثبت نشده است. "
                    "با مدیر سیستم تماس بگیرید."
                ),
            },
            status=400,
        )
    recovery.note_sms_issued(request)
    logger.info("recovery code issued for user %s (sent=%s)", user.pk, result["sent"])
    return JsonResponse(
        {
            "ok": True,
            "stage": "code-sent",
            "phone": result["phone"],
            "resent": result["resent"],
        }
    )


@require_POST
def recover_verify(request):
    data = recovery.session_state(request)
    if data is None:
        return JsonResponse(
            {"ok": False, "error": "درخواست بازیابی منقضی شده؛ دوباره شروع کنید."},
            status=400,
        )

    code = (request.POST.get("code") or "").strip()
    if code != data["code"]:
        data["tries"] = int(data.get("tries", 0)) + 1
        if data["tries"] >= recovery.MAX_VERIFY_ATTEMPTS:
            recovery.clear(request)
            return JsonResponse(
                {"ok": False, "error": "تلاش‌های ناموفق زیاد بود؛ دوباره شروع کنید."},
                status=429,
            )
        request.session[recovery.SESSION_KEY] = data
        request.session.modified = True
        remaining = recovery.MAX_VERIFY_ATTEMPTS - data["tries"]
        return JsonResponse(
            {"ok": False, "error": f"کد وارد شده درست نیست ({remaining} تلاش باقی مانده)."},
            status=400,
        )

    request.session[recovery.SESSION_KEY] = {**data, "verified": True}
    request.session.modified = True
    return JsonResponse({"ok": True, "stage": "verified"})


@require_POST
def recover_reset(request):
    data = recovery.session_state(request)
    if data is None or not data.get("verified"):
        return JsonResponse(
            {"ok": False, "error": "ابتدا کد بازیابی را تأیید کنید."}, status=400
        )

    password1 = request.POST.get("new_password1") or ""
    password2 = request.POST.get("new_password2") or ""
    if password1 != password2:
        return JsonResponse({"ok": False, "error": "دو رمز یکسان نیستند."}, status=400)

    User = get_user_model()
    try:
        user = User.objects.get(pk=data["uid"], is_active=True)
    except User.DoesNotExist:
        recovery.clear(request)
        return JsonResponse({"ok": False, "error": "کاربر یافت نشد."}, status=400)

    try:
        password_validation.validate_password(password1, user=user)
    except Exception as exc:
        messages = [m for m in getattr(exc, "messages", [str(exc)])][:2]
        return JsonResponse({"ok": False, "error": " ".join(messages)}, status=400)

    user.set_password(password1)
    user.save(update_fields=["password"])

    recovery.clear(request)
    logged_in_user = authenticate(request, username=user.username, password=password1)
    if logged_in_user is not None:
        login(request, logged_in_user)
        logger.info("password reset and login for user %s", user.pk)
        return JsonResponse(
            {"ok": True, "stage": "done", "redirect": reverse("admin:index")}
        )
    logger.info("password reset (no auto-login) for user %s", user.pk)
    return JsonResponse(
        {"ok": True, "stage": "done", "redirect": reverse("admin:login")}
    )


@require_POST
def recover_question_start(request):
    """Start security-question recovery: return the question for a username."""
    username = (request.POST.get("username") or "").strip()
    user = recovery.find_recoverable_user(username)
    if user is None:
        return JsonResponse(
            {"ok": False, "error": "کاربری با این نام کاربری پیدا نشد."}, status=400
        )
    if not user.security_question or not user.security_answer_hash:
        recovery.clear(request)
        return JsonResponse(
            {
                "ok": False,
                "error": "برای این حساب سوال امنیتی تنظیم نشده است. با مدیر سیستم تماس بگیرید.",
            },
            status=400,
        )
    if not recovery.question_start_allowed(request):
        return JsonResponse(
            {
                "ok": False,
                "error": "درخواست‌های مکرر؛ لطفاً دقایقی دیگر دوباره تلاش کنید.",
            },
            status=429,
        )
    recovery.question_start_session(user, request)
    recovery.note_question_attempt(request)
    return JsonResponse(
        {"ok": True, "stage": "question", "question": user.security_question}
    )


@require_POST
def recover_question_verify(request):
    """Verify the security answer; on success the reset step unlocks."""
    if recovery.question_invalidated_session(request):
        return JsonResponse(
            {"ok": False, "error": "درخواست بازیابی منقضی شده؛ دوباره شروع کنید."},
            status=400,
        )
    data = request.session[recovery.SESSION_KEY]

    User = get_user_model()
    answer = request.POST.get("answer") or ""
    if not recovery.answer_matches(User.objects.get(pk=data["uid"]), answer):
        recovery.note_question_attempt(request)
        data["tries"] = int(data.get("tries", 0)) + 1
        if data["tries"] >= recovery.MAX_ANSWER_ATTEMPTS:
            recovery.clear(request)
            return JsonResponse(
                {"ok": False, "error": "تلاش‌های ناموفق زیاد بود؛ دوباره شروع کنید."},
                status=429,
            )
        request.session[recovery.SESSION_KEY] = data
        request.session.modified = True
        remaining = recovery.MAX_ANSWER_ATTEMPTS - data["tries"]
        return JsonResponse(
            {"ok": False, "error": f"پاسخ درست نیست ({remaining} تلاش باقی مانده)."},
            status=400,
        )

    request.session[recovery.SESSION_KEY] = {**data, "verified": True}
    request.session.modified = True
    logger.info("security answer verified for user %s", data["uid"])
    return JsonResponse({"ok": True, "stage": "verified"})


def recover_home(request):
    """Standalone password-recovery page (separate from the login page)."""
    return render(request, "admin/recover.html")
