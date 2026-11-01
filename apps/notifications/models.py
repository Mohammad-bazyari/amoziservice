"""SMS models: editable templates and a full delivery log."""
from django.conf import settings
from django.db import models

from apps.core.common import TimeStampedModel


class SmsTemplate(TimeStampedModel):
    """SMS body templates with {placeholders}, editable from admin."""

    name = models.CharField("نام قالب", max_length=80, unique=True)
    label = models.CharField("عنوان نمایشی", max_length=120)
    body = models.TextField(
        "متن پیامک",
        help_text=(
            "می‌توانید از این متغیرها استفاده کنید: "
            "{tracking_code} {customer_name} {customer_phone} {brand} {problem} "
            "{district} {service} {business_name} {city}"
        ),
    )

    class Meta:
        verbose_name = "قالب پیامک"
        verbose_name_plural = "قالب‌های پیامک"
        ordering = ["name"]

    def __str__(self):
        return self.label

    def render(self, context: dict) -> str:
        text = self.body
        for key, value in context.items():
            text = text.replace("{" + key + "}", str(value))
        return text


class SmsLog(TimeStampedModel):
    """One row per delivery attempt. The API key is never stored here."""

    class Status(models.TextChoices):
        PENDING = "pending", "در انتظار ارسال"
        SENT = "sent", "ارسال شد"
        FAILED = "failed", "ناموفق"

    class Provider(models.TextChoices):
        KAVENEGAR = "kavenegar", "کاوه‌نگار"
        MOCK = "mock", "شبیه‌ساز (آزمایشی)"

    request = models.ForeignKey(
        "requests.ServiceRequest", verbose_name="درخواست", on_delete=models.CASCADE,
        related_name="sms_logs", null=True, blank=True,
    )
    recipient = models.CharField("گیرنده", max_length=20)
    sender = models.CharField("فرستنده", max_length=20, blank=True, default="")
    message = models.TextField("متن پیام")
    provider = models.CharField(
        "سرویس‌دهنده", max_length=20, choices=Provider.choices, default=Provider.KAVENEGAR,
    )
    message_id = models.CharField("شناسه پیام (پروایدر)", max_length=120, blank=True, default="")
    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True,
    )
    status_text = models.CharField("شرح وضعیت", max_length=120, blank=True, default="")
    response_data = models.JSONField("پاسخ خام", null=True, blank=True)
    error_message = models.TextField("خطا", blank=True, default="")
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="کاربر", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )

    class Meta:
        verbose_name = "گزارش پیامک"
        verbose_name_plural = "گزارش پیامک‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.recipient} — {self.get_status_display()}"

    def mark_sent(self, message_id: str, status_text: str = "", response: dict | None = None):
        self.status = self.Status.SENT
        self.message_id = message_id or ""
        self.status_text = status_text
        if response is not None:
            self.response_data = response
        self.error_message = ""
        self.save(update_fields=["status", "message_id", "status_text", "response_data", "updated_at"])

    def mark_failed(self, error: str, response: dict | None = None):
        self.status = self.Status.FAILED
        self.error_message = error[:2000]
        if response is not None:
            self.response_data = response
        self.save(update_fields=["status", "error_message", "response_data", "updated_at"])
