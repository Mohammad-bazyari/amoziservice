"""Admin password recovery via SMS code.

No email dependency: the admin enters their username, a 6-digit code is sent
to the mobile number stored on their User record, and they set a new password
after verifying the code. The code lives only in the server-side session and
never leaves except through SMS. SMS uses the shared dispatcher, so in local
development (KAVENEGAR_ENABLED=False) it is logged to SmsLog as a mock send
instead of costing money.
"""
import logging
import secrets
import time

from django.contrib.auth import get_user_model

from apps.notifications.services import dispatcher

logger = logging.getLogger(__name__)

CODE_TTL_SECONDS = 10 * 60  # code validity window
REISSUE_COOLDOWN_SECONDS = 60  # min gap between two codes
MAX_VERIFY_ATTEMPTS = 5  # wrong-code tries before the session is invalidated
SESSION_KEY = "admin_pw_recovery"

# Per-IP SMS issue throttling (abuse guard: an attacker WITHOUT a session
# cookie could otherwise hammer /pw-recover/start/ and burn Kavenegar
# credit). Uses the shared cache; on multi-process deployments each worker
# keeps its own counter, so this is a hard speed bump rather than a global
# guarantee — the per-session cooldown still applies on top of it.
SMS_ISSUE_INTERVAL_SECONDS = 120  # min gap between "start" calls from one IP
SMS_ISSUE_MAX_PER_HOUR = 5  # sliding per-IP cap

RECOVERY_TEMPLATE_NAME = "admin_password_recovery"
DEFAULT_RECOVERY_BODY = (
    "{business_name}\n"
    "کد بازیابی رمز عبور پنل مدیریت: {code}\n"
    "این کد تا ۱۰ دقیقه اعتبار دارد. اگر شما درخواست نداده‌اید، این پیامک را نادیده بگیرید."
)

# ---------------------------------------------------------------------------
# Security-question recovery path (رمز بازیابی با سوال امنیتی)
#
# Same session key/code window as the SMS path but marked method="question";
# once the answer is verified (verified=True) the existing /pw-recover/reset/
# endpoint accepts it unchanged. The answer is stored ONLY as a Django
# password hash on User.security_answer_hash — set via the interactive
# `python manage.py set_security_question` command (never in code or docs).
# ---------------------------------------------------------------------------
MAX_ANSWER_ATTEMPTS = 5  # wrong-answer tries before the session is invalidated
QUESTION_START_INTERVAL_SECONDS = 2  # min gap between "question start" per IP
QUESTION_START_MAX_PER_HOUR = 20  # per-IP hourly cap on answer attempts


def normalize_answer(answer: str) -> str:
    """Collapse whitespace and casefold, so 'Ali  Nazemi' == 'ali nazemi'."""
    return " ".join((answer or "").split()).casefold()


def hash_answer(answer: str) -> str:
    """Hash the normalized answer with Django's salted password hasher."""
    from django.contrib.auth.hashers import make_password

    return make_password(normalize_answer(answer))


def answer_matches(user, answer: str) -> bool:
    from django.contrib.auth.hashers import check_password

    if not user.security_answer_hash:
        return False
    return check_password(normalize_answer(answer), user.security_answer_hash)


def find_recoverable_user(username: str):
    """Return the active staff user for a username, else None."""
    User = get_user_model()
    username = (username or "").strip()
    if not username:
        return None
    return (
        User.objects.filter(username__iexact=username, is_active=True, is_staff=True)
        .first()
    )


def issue_code(user, request) -> dict:
    """Generate a code, SMS it to the user, store it in the session.

    Returns {"sent": bool, "resent": bool, "phone": str} — "sent" is False when
    the user has no phone on file, "resent" is True when the previous code is
    still valid (re-issue cooldown).
    """
    data = request.session.get(SESSION_KEY)
    now = time.time()
    if (
        data
        and data.get("uid") == user.pk
        and now - float(data.get("at", 0)) < REISSUE_COOLDOWN_SECONDS
    ):
        return {"sent": True, "resent": True, "phone": user.phone}

    code = f"{secrets.randbelow(10**6):06d}"
    sent = False
    if user.phone:
        from apps.core.models import SiteSettings

        template = dispatcher.SmsTemplate.objects.filter(name=RECOVERY_TEMPLATE_NAME).first()
        context = {"code": code, "business_name": SiteSettings.load().business_name}
        message = template.render(context) if template else DEFAULT_RECOVERY_BODY.format(**context)
        try:
            dispatcher.attempt_sms(recipient=user.phone, message=message)
            sent = True
        except Exception:  # pragma: no cover — attempt_sms never raises in practice
            logger.exception("recovery SMS failed for user %s", user.pk)

    request.session[SESSION_KEY] = {
        "uid": user.pk,
        "code": code,
        "at": now,
        "tries": 0,
    }
    request.session.modified = True
    logger.info("password recovery code issued for user %s (sent=%s)", user.pk, sent)
    return {"sent": sent, "resent": False, "phone": user.phone}


def _client_ip(request) -> str:
    return request.META.get("REMOTE_ADDR") or "0.0.0.0"


def sms_issue_allowed(request) -> bool:
    """Per-IP throttle for SMS-issuing "start" calls."""
    from django.core.cache import cache

    ip = _client_ip(request)
    last = cache.get(f"pwrec:last:{ip}")
    if last is not None and time.time() - float(last) < SMS_ISSUE_INTERVAL_SECONDS:
        return False
    issued = cache.get(f"pwrec:count:{ip}") or 0
    if int(issued) >= SMS_ISSUE_MAX_PER_HOUR:
        return False
    return True


def note_sms_issued(request) -> None:
    """Record an issued code against the caller's IP for throttling."""
    from django.core.cache import cache

    ip = _client_ip(request)
    cache.set(f"pwrec:last:{ip}", time.time(), timeout=600)
    issued = int(cache.get(f"pwrec:count:{ip}") or 0)
    cache.set(f"pwrec:count:{ip}", issued + 1, timeout=3600)


def question_start_session(user, request) -> None:
    """Mark the session as a pending security-question recovery."""
    request.session[SESSION_KEY] = {
        "uid": user.pk,
        "method": "question",
        "at": time.time(),
        "tries": 0,
    }
    request.session.modified = True
    logger.info("security-question recovery started for user %s", user.pk)


def question_start_allowed(request) -> bool:
    """Per-IP throttle for security-question attempts (slows answer guessing)."""
    from django.core.cache import cache

    ip = _client_ip(request)
    last = cache.get(f"pwrec:q:last:{ip}")
    if last is not None and time.time() - float(last) < QUESTION_START_INTERVAL_SECONDS:
        return False
    attempts = int(cache.get(f"pwrec:q:count:{ip}") or 0)
    if attempts >= QUESTION_START_MAX_PER_HOUR:
        return False
    return True


def note_question_attempt(request) -> None:
    """Record a security-question check against the caller's IP."""
    from django.core.cache import cache

    ip = _client_ip(request)
    cache.set(f"pwrec:q:last:{ip}", time.time(), timeout=30)
    attempts = int(cache.get(f"pwrec:q:count:{ip}") or 0)
    cache.set(f"pwrec:q:count:{ip}", attempts + 1, timeout=3600)


def question_invalidated_session(request) -> bool:
    """True when the session TTL expired for the pending question recovery."""
    data = request.session.get(SESSION_KEY)
    return (
        data is None
        or data.get("method") != "question"
        or time.time() - float(data.get("at", 0)) > CODE_TTL_SECONDS
    )


def session_state(request) -> dict | None:
    """Return the pending recovery session data if it is fresh enough."""
    data = request.session.get(SESSION_KEY)
    if not data:
        return None
    if time.time() - float(data.get("at", 0)) > CODE_TTL_SECONDS:
        return None
    return data


def clear(request) -> None:
    request.session.pop(SESSION_KEY, None)
    request.session.modified = True
