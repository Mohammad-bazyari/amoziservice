"""High-level SMS dispatch: template rendering + guaranteed logging.

The dispatcher NEVER raises and NEVER blocks request saving: every attempt is
persisted as an SmsLog row (pending → sent/failed) so failures are visible and
retryable from the admin panel.
"""
import logging

from apps.notifications.models import SmsLog, SmsTemplate
from apps.notifications.services import kavenegar

logger = logging.getLogger(__name__)

NEW_REQUEST_TEMPLATE_NAME = "new_request_notification"
DEFAULT_NEW_REQUEST_TEMPLATE = (
    "درخواست جدید تعمیر پکیج\n"
    "کد درخواست: {tracking_code}\n"
    "نام: {customer_name}\n"
    "موبایل: {customer_phone}\n"
    "برند: {brand}\n"
    "مشکل: {problem}\n"
    "منطقه: {district}"
)


def _settings():
    from apps.core.models import SiteSettings

    return SiteSettings.load()


def build_new_request_context(req) -> dict:
    """Template context for the new-request notification."""
    from apps.core.models import SiteSettings

    return {
        "tracking_code": req.tracking_code,
        "customer_name": req.customer_name,
        "customer_phone": req.customer_phone,
        "brand": req.brand_display,
        "problem": req.problem_display,
        "district": req.district or "—",
        "service": req.service.name,
        "business_name": SiteSettings.load().business_name,
        "city": req.city,
    }


def render_new_request_message(req) -> str:
    template = SmsTemplate.objects.filter(name=NEW_REQUEST_TEMPLATE_NAME).first()
    context = build_new_request_context(req)
    if template is not None:
        return template.render(context)
    return DEFAULT_NEW_REQUEST_TEMPLATE.format(**context)


def attempt_sms(*, recipient: str, message: str, request_obj=None, user=None) -> SmsLog:
    """Send one SMS and persist the outcome. Returns the SmsLog row.

    The send call itself is wrapped: a provider that raises (network stack,
    a bug) still lands in an accurate FAILED log row instead of leaving an
    orphaned PENDING row behind.
    """
    provider = SmsLog.Provider.KAVENEGAR if kavenegar.sms_enabled() else SmsLog.Provider.MOCK
    log = SmsLog.objects.create(
        request=request_obj,
        recipient=kavenegar.normalize_recipient(recipient),
        message=message,
        provider=provider,
        status=SmsLog.Status.PENDING,
        created_by=user,
    )
    try:
        result = kavenegar.send_sms(recipient=recipient, message=message)
    except Exception as exc:
        logger.exception("send_sms raised for %s", log.recipient)
        log.mark_failed(f"خطای غیرمنتظره: {exc}")
        return log
    log.provider = result.get("provider", log.provider)
    if result["ok"]:
        log.mark_sent(result.get("message_id", ""), result.get("status_text", ""), result.get("raw"))
    else:
        log.mark_failed(result.get("error", "خطای نامشخص"), result.get("raw"))
    return log


def attempt_sms_retry(log: SmsLog, user=None) -> SmsLog:
    """Retry a failed (or pending) SmsLog row in place."""
    result = kavenegar.send_sms(recipient=log.recipient, message=log.message)
    log.provider = result.get("provider", log.provider)
    if result["ok"]:
        log.mark_sent(result.get("message_id", ""), result.get("status_text", ""), result.get("raw"))
    else:
        log.mark_failed(result.get("error", "خطای نامشخص"), result.get("raw"))
    return log


def dispatch_new_request_sms(req, user=None) -> SmsLog | None:
    """Fire the technician notification for a saved request. Never raises."""
    try:
        settings_obj = _settings()
        if not settings_obj.sms_enabled:
            logger.info(
                "SMS disabled in SiteSettings; skipping notification for %s",
                req.tracking_code,
            )
            return None
        message = render_new_request_message(req)
        recipient = settings_obj.sms_recipient or settings_obj.business_phone
        return attempt_sms(recipient=recipient, message=message, request_obj=req, user=user)
    except Exception:
        # Request saving must never depend on SMS delivery.
        logger.exception(
            "dispatch_new_request_sms failed for %s", getattr(req, "tracking_code", "?")
        )
        return None


CUSTOMER_CONFIRM_TEMPLATE_NAME = "customer_request_confirmation"
DEFAULT_CUSTOMER_CONFIRM_BODY = (
    "{business_name}\n"
    "درخواست شما ثبت شد؛ کد پیگیری: {tracking_code}\n"
    "تعمیرکار برای هماهنگی با شما تماس می‌گیرد."
)


def build_customer_confirm_context(req) -> dict:
    """Template context for the customer confirmation SMS."""
    from apps.core.models import SiteSettings

    return {
        "tracking_code": req.tracking_code,
        "customer_name": req.customer_name,
        "service": req.service.name,
        "business_name": SiteSettings.load().business_name,
    }


def render_customer_confirm_message(req) -> str:
    template = SmsTemplate.objects.filter(name=CUSTOMER_CONFIRM_TEMPLATE_NAME).first()
    context = build_customer_confirm_context(req)
    if template is not None:
        return template.render(context)
    return DEFAULT_CUSTOMER_CONFIRM_BODY.format(**context)


def dispatch_customer_confirm_sms(req, user=None) -> SmsLog | None:
    """Send the confirmation SMS to the customer who submitted a request.

    Independent of the technician notification (its own template and its own
    SiteSettings toggle) and, like every dispatcher here, never raises: a
    failed customer SMS never affects the stored request or the technician
    notification.
    """
    try:
        settings_obj = _settings()
        if not settings_obj.customer_sms_enabled:
            logger.info(
                "Customer confirmation SMS disabled; skipping for %s",
                req.tracking_code,
            )
            return None
        message = render_customer_confirm_message(req)
        return attempt_sms(recipient=req.customer_phone, message=message, request_obj=req, user=user)
    except Exception:
        logger.exception(
            "dispatch_customer_confirm_sms failed for %s",
            getattr(req, "tracking_code", "?"),
        )
        return None


def dispatch_request_notifications(req, user=None) -> tuple[SmsLog | None, SmsLog | None]:
    """Fire BOTH notifications for a saved request: technician + customer.

    Used by the request submit flow; each leg is independent, so one failing
    (or disabled) leg never suppresses the other.
    """
    tech = dispatch_new_request_sms(req, user=user)
    customer = dispatch_customer_confirm_sms(req, user=user)
    return tech, customer
