import re as _re

from django.db import models

from apps.core.common import TimeStampedModel


class SiteSettings(TimeStampedModel):
    """Singleton row holding dynamic business information (pk=1).

    Everything here is editable from the Persian admin panel; templates must
    read phone/brand/etc. from this object instead of hardcoding.
    """

    business_name = models.CharField("نام کسب‌وکار", max_length=120, default="اوستا سرویس")
    business_phone = models.CharField("شماره تماس", max_length=20, default="09120832480")
    business_email = models.EmailField("ایمیل", blank=True, default="")
    province = models.CharField("استان", max_length=60, default="تهران")
    city = models.CharField("شهر", max_length=60, default="تهران")
    address = models.TextField("آدرس", blank=True, default="")
    working_hours = models.TextField("ساعات کاری", blank=True, default="")
    logo = models.FileField("لوگو", upload_to="site/", blank=True)
    favicon = models.FileField("فاوآیکون", upload_to="site/", blank=True)

    whatsapp = models.CharField("واتساپ", max_length=40, blank=True, default="")
    instagram = models.CharField("اینستاگرام", max_length=120, blank=True, default="")
    telegram = models.CharField("تلگرام", max_length=120, blank=True, default="")

    default_seo_title = models.CharField(
        "عنوان پیش‌فرض سئو",
        max_length=180,
        default="اوستا سرویس | تعمیر تخصصی پکیج در تهران",
    )
    default_meta_description = models.TextField(
        "توضیح متای پیش‌فرض",
        default="تعمیر پکیج در تهران با ثبت درخواست آنلاین و تماس سریع تعمیرکار.",
    )
    default_og_image = models.FileField("تصویر اشتراک‌گذاری پیش‌فرض", upload_to="seo/", blank=True)

    footer_text = models.TextField("متن فوتر", blank=True, default="")

    inspection_fee = models.PositiveIntegerField(
        "هزینه عیب‌یابی (تومان)",
        default=350000,
        help_text="این مبلغ در صفحه خدمات و فرم درخواست نمایش داده می‌شود (به تومان).",
    )

    sms_enabled = models.BooleanField(
        "ارسال پیامک فعال", default=True,
        help_text="اگر خاموش باشد، هنگام ثبت درخواست جدید پیامکی ارسال نمی‌شود.",
    )
    sms_recipient = models.CharField(
        "شماره دریافت پیامک درخواست‌ها", max_length=20, default="09120832480",
        help_text="شماره تعمیرکار که پیامک درخواست جدید به آن ارسال می‌شود.",
    )
    customer_sms_enabled = models.BooleanField(
        "پیامک تأیید به مشتری", default=True,
        help_text="پس از ثبت درخواست، به خود مشتری هم پیامک تأیید با کد پیگیری ارسال می‌شود.",
    )

    # Models whose text fields follow the business name and must update
    # automatically when it is renamed in the admin panel.
    RENAME_PROPAGATION_MODELS = (
        "core.SiteSettings",
        "content.HomePageContent",
        "content.AboutPageContent",
        "content.ContactPageContent",
        "content.FAQ",
        "content.Brand",
        "content.Service",
        "content.Page",
    )

    class Meta:
        verbose_name = "تنظیمات سایت"
        verbose_name_plural = "تنظیمات سایت"

    def __str__(self):
        return "تنظیمات سایت"

    def save(self, *args, **kwargs):
        self.pk = 1
        rename = None
        if not self._state.adding:
            old = type(self).objects.filter(pk=self.pk).first()
            if old and old.business_name != self.business_name:
                rename = (old.business_name, self.business_name)
        super().save(*args, **kwargs)
        if rename:
            self.propagate_business_rename(*rename)

    def propagate_business_rename(self, old_name, new_name):
        """Replace every occurrence of the old business name with the new one
        across all CMS text fields, so a rename in the panel reaches every
        section of the site (SEO title, benefits title, about page, FAQs...).
        Returns the number of updated rows."""
        old_name, new_name = (old_name or "").strip(), (new_name or "").strip()
        if not old_name or not new_name or old_name == new_name:
            return 0
        # (?<!و) guards against re-matching a name already inside the new one.
        pattern = _re.compile("(?<!و)" + _re.escape(old_name))
        from django.apps import apps

        changed = 0
        for label in self.RENAME_PROPAGATION_MODELS:
            try:
                model = apps.get_model(label)
            except LookupError:
                continue
            for field in model._meta.concrete_fields:
                if not isinstance(field, (models.CharField, models.TextField)):
                    continue
                if field.attname == "slug":
                    continue
                qs = model.objects.filter(**{f"{field.name}__contains": old_name})
                for row in qs:
                    old_val = getattr(row, field.attname) or ""
                    new_val = pattern.sub(new_name, old_val)
                    if new_val != old_val:
                        setattr(row, field.attname, new_val)
                        row.save(update_fields=[field.attname])
                        if row.pk == self.pk:
                            setattr(self, field.attname, new_val)
                        changed += 1
        return changed

    @property
    def effective_seo_title(self):
        """SEO title that always carries the current business name, even when
        the stored default is blank."""
        return self.default_seo_title or f"{self.business_name} | تعمیر تخصصی پکیج در {self.city}"

    @classmethod
    def load(cls):
        obj, _created = cls.objects.get_or_create(pk=1)
        return obj

    @property
    def phone_href(self) -> str:
        """tel: link target derived from the stored phone."""
        digits = "".join(ch for ch in self.business_phone if ch.isdigit())
        if digits.startswith("0"):
            digits = "+98" + digits[1:]
        return f"tel:{digits}"

    @property
    def whatsapp_href(self) -> str:
        if not self.whatsapp:
            return ""
        digits = "".join(ch for ch in self.whatsapp if ch.isdigit())
        return f"https://wa.me/{digits}"
