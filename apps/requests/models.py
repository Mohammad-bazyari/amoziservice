"""Service request models: the request, its status history, and private notes."""
import secrets

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone

from apps.core.common import TimeStampedModel

phone_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره موبایل باید ۱۱ رقم و با 09 شروع شود.",
)


class ServiceRequest(TimeStampedModel):
    """A customer repair request (no accounts, phone-based)."""

    class Status(models.TextChoices):
        NEW = "new", "جدید"
        CONTACTED = "contacted", "تماس گرفته شد"
        CONFIRMED = "confirmed", "تأیید شد"
        IN_PROGRESS = "in_progress", "در حال انجام"
        COMPLETED = "completed", "تکمیل شده"
        CANCELLED = "cancelled", "لغو شده"

    tracking_code = models.CharField(
        "کد پیگیری",
        max_length=16,
        unique=True,
        editable=False,
        db_index=True,
    )
    service = models.ForeignKey(
        "content.Service",
        verbose_name="خدمت",
        on_delete=models.PROTECT,
        related_name="requests",
    )
    brand = models.ForeignKey(
        "content.Brand",
        verbose_name="برند",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="requests",
    )
    other_brand_name = models.CharField(
        "نام برند دیگر", max_length=120, blank=True, default=""
    )
    problem = models.ForeignKey(
        "content.ProblemOption",
        verbose_name="مشکل",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requests",
    )
    other_problem_label = models.CharField(
        "توضیح مشکل آزاد", max_length=250, blank=True, default=""
    )
    description = models.TextField("شرح مشکل", blank=True, default="")

    customer_name = models.CharField("نام و نام خانوادگی", max_length=120)
    customer_phone = models.CharField(
        "شماره موبایل", max_length=11, validators=[phone_validator], db_index=True
    )

    province = models.CharField("استان", max_length=60, default="تهران")
    city = models.CharField("شهر", max_length=60, default="تهران")
    district = models.CharField("منطقه", max_length=80, blank=True, default="")
    address = models.TextField("آدرس")
    plaque = models.CharField("پلاک", max_length=20, blank=True, default="")
    unit = models.CharField("واحد", max_length=10, blank=True, default="")
    postal_code = models.CharField("کد پستی", max_length=10, blank=True, default="")
    address_notes = models.TextField("توضیحات آدرس", blank=True, default="")

    status = models.CharField(
        "وضعیت", max_length=20, choices=Status.choices, default=Status.NEW, db_index=True
    )
    completed_at = models.DateTimeField("تاریخ تکمیل", null=True, blank=True)

    ip_address = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        verbose_name = "درخواست تعمیر"
        verbose_name_plural = "درخواست‌های تعمیر"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "-created_at"]),
            models.Index(fields=["customer_phone"]),
        ]

    def __str__(self):
        return f"{self.tracking_code} — {self.customer_name}"

    # --- tracking code -------------------------------------------------
    @staticmethod
    def _generate_tracking_code() -> str:
        """Human-friendly code like BR-1025 (no leading zero, not starting at 0)."""
        return f"BR-{secrets.randbelow(9000) + 1000}"

    def assign_tracking_code(self):
        """Assign a unique 4-digit tracking code; retries on collision."""
        for _attempt in range(50):
            candidate = self._generate_tracking_code()
            if not type(self).objects.filter(tracking_code=candidate).exists():
                self.tracking_code = candidate
                return candidate
        raise RuntimeError("Could not generate a unique tracking code")

    def save(self, *args, **kwargs):
        if not self.tracking_code:
            self.assign_tracking_code()
        is_new_status_completed = (
            self.status == self.Status.COMPLETED and not self.completed_at
        )
        super().save(*args, **kwargs)
        if is_new_status_completed:
            type(self).objects.filter(pk=self.pk).update(
                completed_at=timezone.now()
            )

    # --- state transitions ---------------------------------------------
    def set_status(self, new_status, *, changed_by=None, note=""):
        """Change status and always write a history row."""
        old = self.status
        if new_status == old:
            return
        self.status = new_status
        self.save(update_fields=["status", "updated_at"])
        RequestStatusHistory.objects.create(
            request=self,
            from_status=old,
            to_status=new_status,
            changed_by=changed_by,
            note=note,
        )

    # --- form helpers ---------------------------------------------------
    def clean(self):
        super().clean()
        if self.brand_id:
            return
        # Phone-in orders logged by the operator from the admin panel may lack
        # any brand info; the public wizard always supplies one of the two.
        if getattr(self, "_brand_optional", False):
            return
        if not (self.other_brand_name or "").strip():
            raise ValidationError(
                {"other_brand_name": "اگر برند را انتخاب نکرده‌اید، نام آن را وارد کنید."}
            )

    @property
    def brand_display(self) -> str:
        return self.brand.name if self.brand_id else (self.other_brand_name or "—")

    @property
    def problem_display(self) -> str:
        if self.problem_id:
            return self.problem.label
        return self.other_problem_label or "—"

    @property
    def status_label(self) -> str:
        return self.get_status_display()


class RequestStatusHistory(TimeStampedModel):
    """Audit log: every status change of every request."""

    request = models.ForeignKey(
        ServiceRequest, verbose_name="درخواست", on_delete=models.CASCADE,
        related_name="status_history",
    )
    from_status = models.CharField("از وضعیت", max_length=20, choices=ServiceRequest.Status.choices)
    to_status = models.CharField("به وضعیت", max_length=20, choices=ServiceRequest.Status.choices)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="تغییردهنده", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    note = models.CharField("یادداشت", max_length=250, blank=True, default="")

    class Meta:
        verbose_name = "تاریخچه وضعیت"
        verbose_name_plural = "تاریخچه وضعیت‌ها"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.request.tracking_code}: {self.from_status} → {self.to_status}"


class RequestNote(TimeStampedModel):
    """Private admin note; never shown to customers."""

    request = models.ForeignKey(
        ServiceRequest, verbose_name="درخواست", on_delete=models.CASCADE,
        related_name="notes",
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name="نویسنده", on_delete=models.SET_NULL,
        null=True, blank=True, related_name="+",
    )
    body = models.TextField("متن یادداشت")

    class Meta:
        verbose_name = "یادداشت داخلی"
        verbose_name_plural = "یادداشت‌های داخلی"
        ordering = ["-created_at"]

    def __str__(self):
        return f"یادداشت {self.request.tracking_code}"


def request_image_upload_to(instance, filename):
    return f"request-images/{instance.request_id}/{filename}"


class RequestImage(TimeStampedModel):
    """Optional customer-uploaded boiler/error images."""

    request = models.ForeignKey(
        ServiceRequest, verbose_name="درخواست", on_delete=models.CASCADE,
        related_name="images",
    )
    image = models.FileField("تصویر", upload_to=request_image_upload_to)
    original_filename = models.CharField("نام فایل اصلی", max_length=255, blank=True, default="")
    content_type = models.CharField("نوع فایل", max_length=100, blank=True, default="")
    size_bytes = models.PositiveIntegerField("حجم (بایت)", default=0)

    class Meta:
        verbose_name = "تصویر درخواست"
        verbose_name_plural = "تصاویر درخواست"
