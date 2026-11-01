"""Kavenegar REST API client.

Docs: https://kavenegar.com/rest.html  (v1 JSON API, API key in the path)

The API key lives in the KAVENEGAR_API_KEY environment variable and is only
used server-side here. When KAVENEGAR_ENABLED is falsey, a deterministic mock
provider is used so local development and tests never send paid SMS.
"""
import uuid
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.kavenegar.com/v1"
TIMEOUT_SECONDS = 10

# Kavenegar numeric message statuses (subset of documented values).
KAVENEGAR_STATUS_TEXT = {
    1: "در صف ارسال",
    2: "زمان‌بندی شده",
    4: "ارسال شد",
    5: "ناموفق",
    6: "ارسال نشده (غیرفعال)",
    8: "رسیده به اپراتور",
    10: "ارسال به اپراتور",
    11: "دریافت نشده",
    13: "لغو شده",
    14: "خطا در ارسال",
}


class KavenegarError(Exception):
    """Raised for protocol-level problems with the Kavenegar API."""


def normalize_recipient(phone: str) -> str:
    """Normalize 09xxxxxxxxx to 989xxxxxxxxx (Kavenegar's expected format).

    نرمال‌سازی محلی از منبع واحد (apps/requests/phone.py) می‌آید تا
    «+98…» و «0098…» و ارقام فارسی هم مثل فرم درخواست پذیرفته شوند.
    """
    from apps.requests.phone import normalize_mobile

    digits = normalize_mobile(phone)
    if digits.startswith("0"):
        digits = "98" + digits[1:]
    return digits


def sms_enabled() -> bool:
    return bool(getattr(settings, "KAVENEGAR_ENABLED", False))


def _request(path: str, params: dict) -> dict:
    """Call the Kavenegar API and return parsed JSON; raise on hard errors."""
    api_key = getattr(settings, "KAVENEGAR_API_KEY", "")
    if not api_key:
        raise KavenegarError("KAVENEGAR_API_KEY تنظیم نشده است.")
    url = f"{BASE_URL}/{api_key}/{path}"
    try:
        response = requests.post(url, data=params, timeout=TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        raise KavenegarError(f"خطای شبکه هنگام تماس با کاوه‌نگار: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise KavenegarError(f"پاسخ نامعتبر از کاوه‌نگار (HTTP {response.status_code})") from exc

    return_status = (data.get("return") or {}).get("status")
    if response.status_code != 200 or return_status != 200:
        message = (data.get("return") or {}).get("message") or f"HTTP {response.status_code}"
        raise KavenegarError(f"خطای کاوه‌نگار: {message}")
    return data


def send_sms(*, recipient: str, message: str, sender: str | None = None) -> dict:
    """Send one SMS. Never raises; returns a result dict.

    Result shape:
        {"ok": bool, "provider": "kavenegar"|"mock", "message_id": str,
         "status_text": str, "raw": dict|None, "error": str}
    """
    recipient = normalize_recipient(recipient)
    sender = sender or getattr(settings, "KAVENEGAR_SENDER", "") or None

    if not sms_enabled():
        logger.info("SMS mock send to %s (KAVENEGAR_ENABLED=False)", recipient)
        return {
            "ok": True,
            "provider": "mock",
            "message_id": f"mock-{uuid.uuid4().hex[:12]}",
            "status_text": "شبیه‌سازی ارسال (KAVENEGAR_ENABLED=False)",
            "raw": {"receptor": recipient, "message": message, "mock": True},
            "error": "",
        }

    try:
        params = {"receptor": recipient, "message": message}
        if sender:
            params["sender"] = sender
        data = _request("sms/send.json", params)
    except KavenegarError as exc:
        return {"ok": False, "provider": "kavenegar", "message_id": "",
                "status_text": "", "raw": None, "error": str(exc)}

    entries = data.get("entries") or []
    entry = entries[0] if entries else {}
    return {
        "ok": True,
        "provider": "kavenegar",
        "message_id": str(entry.get("messageid", "")),
        "status_text": entry.get("statustext", ""),
        "raw": data,
        "error": "",
    }


def check_sms_status(message_id: str) -> dict:
    """Query delivery status of a previously sent message. Never raises."""
    if not message_id:
        return {"ok": False, "status_code": None, "status_text": "شناسه پیام خالی است.", "raw": None}

    if not sms_enabled():
        return {"ok": True, "status_code": 4, "status_text": "شبیه‌سازی: ارسال شد", "raw": {"mock": True}}

    try:
        data = _request("sms/status.json", {"messageid": message_id})
    except KavenegarError as exc:
        return {"ok": False, "status_code": None, "status_text": str(exc), "raw": None}

    entries = data.get("entries") or []
    entry = entries[0] if entries else {}
    status_code = entry.get("status")
    return {
        "ok": True,
        "status_code": status_code,
        "status_text": KAVENEGAR_STATUS_TEXT.get(status_code, entry.get("statustext", "")),
        "raw": data,
    }
