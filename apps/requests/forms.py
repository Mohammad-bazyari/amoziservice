"""Multi-step request wizard forms.

All wizard steps are validated server-side; the JS in the template only
improves UX. Uploaded images are validated for extension, declared MIME type,
actual content (Pillow), size and count.
"""
import re

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.text import get_valid_filename

from apps.brands.models import Brand
from apps.content.models import ProblemOption, Service
from apps.requests import messages as txt
from apps.requests.phone import normalize_mobile

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME = {"image/jpeg", "image/png", "image/webp"}

# قواعد و متن‌های مشترک سرور و کلاینت از مرجع واحد می‌آیند:
# apps/requests/messages.py (و ترجمه‌ی اپ در locale/fa) — قالب همین الگو را
# در data-pattern می‌گذارد و پیام را در data-error-pattern؛ بنابراین
# اعتبارسنجی مرورگر دقیقاً همان قاعده و همان لحن سرور است.
PHONE_PATTERN = txt.PHONE_PATTERN
PHONE_ERROR = txt.PHONE_ERROR
POSTAL_CODE_PATTERN = txt.POSTAL_CODE_PATTERN
POSTAL_CODE_ERROR = txt.POSTAL_CODE_ERROR


class WizardAriaMixin:
    """پیام خطای هر میدان را با aria به خود کنترل وصل می‌کند.

    قالب پیام را رندر می‌کند و شناسه‌ی ثابت «<auto_id>-error» را روی آن
    می‌گذارد؛ اینجا فقط aria-invalid و aria-describedby روی همان کنترل ست
    می‌شود تا صفحه‌خوان بداند کدام میدان خطا دارد و پیامش کجاست.

    روی full_clean() سوار می‌شود (نه __init__) چون جنگو اعتبارسنجی را
    تنبل انجام می‌دهد و زیرکلاس‌ها (مثل StepProblemForm) وضعیت خود را پس از
    super().__init__() می‌سازند.
    """

    # پیام «الزامی» از مرجع واحد می‌آید (apps/requests/messages.py) و عمداً
    # با متن سمت کلاینت (wizard-form.js) یکسان است تا صفحه و اعلان‌ها
    # یک صدا باشند.
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.error_messages.setdefault("required", txt.REQUIRED)

    def full_clean(self):
        super().full_clean()
        for name in self._errors or {}:
            if name == "__all__":
                continue
            bound = self[name]
            attrs = bound.field.widget.attrs
            attrs["aria-invalid"] = "true"
            described = [item for item in (attrs.get("aria-describedby") or "").split() if item]
            error_id = f"{bound.auto_id}-error"
            if error_id not in described:
                described.append(error_id)
            attrs["aria-describedby"] = " ".join(described)


def validate_image_file(f) -> None:
    """Validate one uploaded file: extension, MIME, size and real content."""
    import os

    ext = os.path.splitext(get_valid_filename(f.name))[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError(txt.IMAGE_FORMAT_ERROR)
    mime = (getattr(f.file, "content_type", "") or "").lower()
    if mime and mime not in ALLOWED_IMAGE_MIME:
        raise ValidationError(txt.IMAGE_MIME_ERROR)
    max_bytes = settings.REQUEST_IMAGE_MAX_BYTES
    if f.size > max_bytes:
        raise ValidationError(txt.image_size_error(max_bytes))
    # Real-content check via Pillow (blocks disguised executables).
    try:
        from PIL import Image

        position = f.file.tell()
        image = Image.open(f.file)
        image.verify()
        f.file.seek(position)
    except Exception as exc:
        raise ValidationError(txt.IMAGE_INVALID_ERROR) from exc


class StepServiceForm(WizardAriaMixin, forms.Form):
    """Step 1: which service is needed (list is CMS-managed)."""

    service_choice = forms.ChoiceField(label="چه کاری لازم دارید؟", widget=forms.RadioSelect)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        choices = [
            (str(s.pk), s.name)
            for s in Service.objects.filter(active=True).order_by("sort_order", "id")
        ]
        self.fields["service_choice"].choices = choices


class MultipleFileInput(forms.ClearableFileInput):
    """File input that accepts multiple files (Django's built-in doesn't)."""

    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField returning the full list of uploaded files."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput)
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if self.widget.allow_multiple_selected and isinstance(data, list):
            result = [super(MultipleFileField, self).clean(d, initial) for d in data]
            if all(f is None for f in result) and not self.required:
                return None
            return [f for f in result if f is not None]
        return super().clean(data, initial)


def _extract_device_name(service_name: str) -> str:
    """Extract device noun from service title (e.g. 'تعمیر پکیج' -> 'پکیج')."""
    if not service_name:
        return "دستگاه"
    text = service_name.strip()
    prefixes = [
        "تعمیر و سرویس",
        "سرویس و تعمیر",
        "تعمیرات",
        "تعمیر",
        "سرویس",
        "نصب و تعمیر",
        "نصب و راه‌اندازی",
        "نصب و راه اندازی",
        "نصب",
    ]
    for prefix in prefixes:
        if text.startswith(prefix):
            remainder = text[len(prefix):].strip()
            if remainder:
                return remainder
    return text or "دستگاه"


class StepProblemForm(WizardAriaMixin, forms.Form):
    """Step 2: brand (select or free-text "other") + the problem itself.

    Options are scoped to the service chosen in step 1: brands and problems
    belong to that service directly (FK), so only its own items are offered.
    """

    brand_choice = forms.ChoiceField(
        label="برند دستگاه شما",
        widget=forms.Select(attrs={"class": "wizard-select", "x-model": "brand"}),
        error_messages={"invalid_choice": txt.INVALID_CHOICE},
    )
    other_brand_name = forms.CharField(
        label="نام برند",
        max_length=120,
        required=False,
        widget=forms.TextInput(attrs={"class": "wizard-input", "placeholder": "نام برند دستگاه را بنویسید"}),
    )
    problem_choice = forms.ChoiceField(
        label="مشکل دستگاه",
        widget=forms.RadioSelect,
        error_messages={"invalid_choice": txt.INVALID_CHOICE},
    )
    other_problem_label = forms.CharField(
        label="شرح مشکل",
        max_length=250,
        required=False,
        widget=forms.TextInput(attrs={"class": "wizard-input", "placeholder": "مشکل را در یک جمله بنویسید"}),
    )
    images = MultipleFileField(
        label="تصاویر دستگاه یا ارور (اختیاری)",
        required=False,
        widget=MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "multiple": True, "aria-describedby": "wizard-step-hint"}),
    )
    description = forms.CharField(
        label="توضیحات بیشتر (اختیاری)",
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"class": "wizard-input", "rows": 3, "placeholder": "هر نکته‌ای که به تشخیص مشکل کمک می‌کند"}),
    )

    def __init__(self, *args, service=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.service = service
        if service is not None:
            brands = service.brands.filter(active=True)
            problems = service.problems.filter(active=True)
            device_label = _extract_device_name(service.name)
        else:
            # review path: the items were already validated against the
            # service at step time; keep the labels the session carried.
            brands = Brand.objects.none()
            problems = ProblemOption.objects.none()
            device_label = "دستگاه"
        brand_choices = [(str(b.pk), b.name) for b in brands]
        problem_choices = [(str(p.pk), p.label) for p in problems]
        # Services the admin has not configured yet (no brands / no problem
        # options): instead of a list whose only choice is «سایر», fall back
        # to plain free-text fields so the customer just types it. The list
        # widget becomes a hidden "other" so validation stays uniform.
        self.no_brand_list = not brand_choices
        if self.no_brand_list:
            self.fields["brand_choice"].choices = [("other", "سایر")]
            self.fields["brand_choice"].widget = forms.HiddenInput()
            self.fields["brand_choice"].initial = "other"
            self.fields["brand_choice"].required = False  # normalized to "other" in clean()
            self.fields["other_brand_name"].required = True
            self.fields["other_brand_name"].label = f"برند {device_label} شما"
            self.fields["other_brand_name"].widget.attrs["placeholder"] = "نام برند دستگاه را بنویسید"
        else:
            brand_choices.append(("other", "سایر (نام برند را می‌نویسم)"))
            self.fields["brand_choice"].choices = brand_choices
            self.fields["brand_choice"].label = f"برند {device_label} شما"
        self.no_problem_list = not problem_choices
        if self.no_problem_list:
            self.fields["problem_choice"].choices = [("other", "سایر")]
            self.fields["problem_choice"].widget = forms.HiddenInput()
            self.fields["problem_choice"].initial = "other"
            self.fields["problem_choice"].required = False  # normalized to "other" in clean()
            self.fields["other_problem_label"].required = True
            self.fields["other_problem_label"].label = f"مشکل {device_label}"
            self.fields["other_problem_label"].widget.attrs["placeholder"] = "مثلاً روشن نمی‌شود، آب نمی‌دهد و ..."
        else:
            problem_choices.append(("other", "سایر"))
            self.fields["problem_choice"].choices = problem_choices
            self.fields["problem_choice"].label = f"مشکل {device_label}"
            # «شرح مشکل» only appears when the customer picks «سایر» and is
            # then mandatory (client-side via Alpine; server-side in clean()).
            self.fields["other_problem_label"].widget.attrs[":required"] = "problem === 'other'"

    def clean_images(self):
        files = self.cleaned_data.get("images") or []
        if not files:
            return None
        max_count = settings.REQUEST_IMAGE_MAX_COUNT
        if len(files) > max_count:
            raise ValidationError(txt.image_count_error(max_count))
        for f in files:
            validate_image_file(f)
        return files

    def clean(self):
        cleaned = super().clean()
        if self.service is None:
            raise ValidationError(txt.SERVICE_REQUIRED)
        # Hidden list widgets (service without configured items) submit "" or
        # nothing at all — always treat them as "other" (free-text mode).
        if getattr(self, "no_brand_list", False):
            cleaned["brand_choice"] = "other"
        if getattr(self, "no_problem_list", False):
            cleaned["problem_choice"] = "other"
        # Every choice must belong to the chosen service (hard ownership).
        brand_val = cleaned.get("brand_choice")
        if brand_val not in (None, "", "other"):
            if not self.service.brands.filter(pk=brand_val, active=True).exists():
                self.add_error("brand_choice", txt.INVALID_CHOICE)
        problem_val = cleaned.get("problem_choice")
        if problem_val not in (None, "", "other"):
            if not self.service.problems.filter(pk=problem_val, active=True).exists():
                self.add_error("problem_choice", txt.INVALID_CHOICE)
        if cleaned.get("brand_choice") == "other" and not (cleaned.get("other_brand_name") or "").strip():
            self.add_error("other_brand_name", txt.BRAND_REQUIRED)
        if cleaned.get("problem_choice") == "other" and not (cleaned.get("other_problem_label") or "").strip():
            self.add_error("other_problem_label", txt.PROBLEM_REQUIRED)
        return cleaned


class StepCustomerForm(WizardAriaMixin, forms.Form):
    customer_name = forms.CharField(
        label="نام و نام خانوادگی",
        max_length=120,
        widget=forms.TextInput(attrs={"class": "wizard-input", "placeholder": "مثلاً علی محمدی", "autocomplete": "name"}),
    )
    # RegexField نیست: قبل از اعتبارسنجی شماره نرمال می‌شود (+98، 0098،
    # صفرِ بلعیده‌شده و ارقام فارسی همه به «09xxxxxxxxx» می‌رسند —
    # apps/requests/phone.py منبع واحد است و با الگوی کلاینت در data-phone
    # و data-pattern همبسته می‌مانند.
    customer_phone = forms.CharField(
        label="شماره موبایل",
        max_length=20,  # فرم خام جا برای «+98 912 …»؛ ویلی پس از نرمال: ۱۱ رقم
        widget=forms.TextInput(
            attrs={
                "inputmode": "tel",
                "dir": "ltr",
                "class": "num wizard-input",
                "placeholder": "۰۹۱۲۱۲۳۴۵۶۷",
                "autocomplete": "tel-national",
                "data-pattern": PHONE_PATTERN,
                "data-error-pattern": PHONE_ERROR,
                "data-phone": "",  # کلاینت هم همین نرمال‌سازی را اجرا می‌کند
            }
        ),
    )

    def clean_customer_phone(self):
        raw = self.cleaned_data.get("customer_phone") or ""
        value = normalize_mobile(raw)
        if not re.fullmatch(rf"^({PHONE_PATTERN})$", value):
            raise ValidationError(PHONE_ERROR)
        return value


class StepAddressForm(WizardAriaMixin, forms.Form):
    city = forms.CharField(label="شهر", max_length=60, initial="تهران", widget=forms.TextInput(attrs={"class": "wizard-input"}))
    district = forms.CharField(
        label="منطقه / محله",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"class": "wizard-input", "placeholder": "مثلاً پونک", "autocomplete": "address-level3"}),
    )
    address = forms.CharField(
        label="آدرس کامل",
        widget=forms.Textarea(attrs={"class": "wizard-input", "rows": 3, "placeholder": "خیابان، کوچه، نام ساختمان و ...", "autocomplete": "street-address"}),
    )
    plaque = forms.CharField(label="پلاک", max_length=20, required=False, widget=forms.TextInput(attrs={"class": "wizard-input"}))
    unit = forms.CharField(label="واحد", max_length=10, required=False, widget=forms.TextInput(attrs={"class": "wizard-input"}))
    address_notes = forms.CharField(label="توضیحات آدرس (اختیاری)", required=False, widget=forms.Textarea(attrs={"class": "wizard-input", "rows": 2}))


class StepImagesForm(WizardAriaMixin, forms.Form):
    """Legacy form kept for backward compatibility; images are now submitted on StepProblemForm."""

    images = MultipleFileField(
        label="تصاویر پکیج یا پیغام خطا (اختیاری)",
        required=False,
        widget=MultipleFileInput(attrs={"accept": "image/jpeg,image/png,image/webp", "multiple": True, "aria-describedby": "wizard-step-hint"}),
    )

    def clean_images(self):
        files = self.cleaned_data.get("images") or []
        if not files:
            return None
        max_count = settings.REQUEST_IMAGE_MAX_COUNT
        if len(files) > max_count:
            raise ValidationError(txt.image_count_error(max_count))
        for f in files:
            validate_image_file(f)
        return files
