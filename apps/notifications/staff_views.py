"""Staff-only SMS actions (status check, retry) used from the admin panel."""
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.notifications.models import SmsLog
from apps.notifications.services import kavenegar
from apps.notifications.services.dispatcher import attempt_sms_retry


def _safe_next(request, default):
    candidate = request.POST.get("next") or request.GET.get("next")
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return candidate
    return default


@staff_member_required
@require_POST
def sms_check_status(request, log_id):
    log = get_object_or_404(SmsLog, pk=log_id)
    if not log.message_id:
        messages.warning(request, "این پیامک شناسه معتبری برای استعلام وضعیت ندارد.")
        return redirect(_safe_next(request, reverse("admin:index")))
    result = kavenegar.check_sms_status(log.message_id)
    if result["ok"]:
        log.status_text = result.get("status_text", "")
        log.response_data = result.get("raw")
        log.save(update_fields=["status_text", "response_data", "updated_at"])
        messages.success(request, f"وضعیت پیامک: {result.get('status_text') or 'نامشخص'}")
    else:
        messages.error(request, result.get("status_text") or "استعلام وضعیت ناموفق بود.")
    return redirect(_safe_next(request, reverse("admin:index")))


@staff_member_required
@require_POST
def sms_retry(request, log_id):
    log = get_object_or_404(SmsLog, pk=log_id)
    updated = attempt_sms_retry(log, user=request.user)
    if updated.status == SmsLog.Status.SENT:
        messages.success(request, "پیامک با موفقیت ارسال شد.")
    else:
        messages.error(request, f"ارسال پیامک ناموفق بود: {updated.error_message or 'خطای نامشخص'}")
    return redirect(_safe_next(request, reverse("admin:index")))
