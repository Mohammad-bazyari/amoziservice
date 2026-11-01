"""Content and CMS models: brands, services, problems, homepage/about/contact copy, FAQ, pages."""
from django.db import models

from apps.core.common import SlugAutoMixin, TimeStampedModel, SEOMixin


def _brand_logo_upload_to(instance, filename):
    return f"brands/{instance.slug}/{filename}"


# Which chip background keeps a brand logo legible in the carousel. Brand marks
# are designed for one background or the other (Baxi is dark blue, Iran
# Radiator is white-on-transparent), so the owner picks the chip per brand and
# new brands can be added without touching code or CSS.
LOGO_THEME_LIGHT = "light"
LOGO_THEME_DARK = "dark"
LOGO_THEME_CHOICES = (
    (LOGO_THEME_LIGHT, "روشن — برای لوگوی تیره یا رنگی"),
    (LOGO_THEME_DARK, "تیره — برای لوگوی سفید یا روشن"),
)


class Brand(SlugAutoMixin, TimeStampedModel, SEOMixin):
    """A device brand, always owned by exactly one Service.

    A brand only means something in the context of the service it belongs to
    (e.g. پکیج بوتان exists because the "تعمیر پکیج" service exists); it is
    offered in the request wizard of that service only and its landing page
    is branded with the owning service.
    """

    service = models.ForeignKey(
        "content.Service",
        verbose_name="خدمت مربوطه",
        on_delete=models.PROTECT,
        related_name="brands",
        help_text="این برند فقط در فرم درخواست همین خدمت و در صفحه آن خدمت نمایش داده می‌شود.",
    )
    name = models.CharField("نام برند", max_length=120)
    slug = models.SlugField(
        "اسلاگ (آدرس صفحه)",
        max_length=140,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خالی بگذارید تا خودکار از نام ساخته شود.",
    )
    short_description = models.TextField("توضیح کوتاه", blank=True, default="")
    content = models.TextField("محتوای صفحه", blank=True, default="")
    image = models.FileField("تصویر", upload_to=_brand_logo_upload_to, blank=True)
    logo_theme = models.CharField(
        "پس‌زمینه کارت لوگو",
        max_length=5,
        choices=LOGO_THEME_CHOICES,
        default=LOGO_THEME_LIGHT,
        help_text="لوگوی تیره روی کارت روشن و لوگوی سفید روی کارت تیره خوانا می‌ماند (در حالت شب هم همین می‌ماند).",
    )
    active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)

    class Meta:
        verbose_name = "برند"
        verbose_name_plural = "برندها"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("brands:detail", kwargs={"slug": self.slug})

    @property
    def content_lines(self):
        """Content split into paragraphs for clean template rendering."""
        return [p.strip() for p in (self.content or "").split("\n") if p.strip()]


class Service(SlugAutoMixin, TimeStampedModel, SEOMixin):
    """A service the business offers (e.g. تعمیر پکیج). Extensible later."""

    name = models.CharField("نام خدمت", max_length=120)
    slug = models.SlugField(
        "اسلاگ (آدرس صفحه)",
        max_length=140,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خالی بگذارید تا خودکار از نام خدمت ساخته شود.",
    )
    short_description = models.TextField("توضیح کوتاه", blank=True, default="")
    content = models.TextField("محتوای کامل", blank=True, default="")
    icon = models.CharField("نام آیکون (lucide)", max_length=60, blank=True, default="wrench")
    image = models.FileField("تصویر", upload_to="services/%Y/%m/", blank=True)
    active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)

    class Meta:
        verbose_name = "خدمت"
        verbose_name_plural = "خدمات"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("services:detail", kwargs={"slug": self.slug})

    @property
    def content_lines(self):
        """Content split into paragraphs for clean template rendering."""
        return [p.strip() for p in (self.content or "").split("\n") if p.strip()]


class ServiceArea(SlugAutoMixin, TimeStampedModel, SEOMixin):
    """A local SEO landing page: this service delivered in one city/area.

    Each row is a dedicated page like «تعمیر پکیج در کرج» — a real demand
    cluster from local searches. It inherits everything (brands, problems,
    FAQ) from its owning Service so the operator only writes the local intro;
    duplicate content is avoided because the area page reuses the service's
    building blocks under its own headline.
    """

    slug_source = "area"
    slug_parts = ("area", "service__name")

    service = models.ForeignKey(
        "content.Service",
        verbose_name="خدمت مربوطه",
        on_delete=models.PROTECT,
        related_name="areas",
        help_text="صفحه منطقه‌ای همیشه زیر یکی از خدمت‌ها ساخته می‌شود.",
    )
    area = models.CharField("نام منطقه/شهر", max_length=120, help_text="مثلاً کرج، اسلامشهر، شهرقدس.")
    slug = models.SlugField(
        "اسلاگ (آدرس صفحه)",
        max_length=140,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خالی بگذارید تا خودکار از نام منطقه ساخته شود.",
    )
    intro = models.TextField("مقدمه محلی", blank=True, default="", help_text="۲ تا ۳ جمله درباره شرایط سرویس در همین منطقه؛ همین متن زیر تیتر صفحه می‌آید.")
    content = models.TextField("محتوای کامل", blank=True, default="", help_text="هر پاراگراف در یک خط؛ خط‌های اول هر بلوک به‌صورت تیتر نمایش داده می‌شوند اگر با ## شروع شوند.")
    active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب نمایش", default=0)

    class Meta:
        verbose_name = "منطقه خدمات"
        verbose_name_plural = "مناطق خدمات"
        ordering = ["sort_order", "area"]
        constraints = [
            models.UniqueConstraint(
                fields=["service", "area"], name="unique_area_per_service"
            )
        ]

    def __str__(self):
        return f"{self.service.name} در {self.area}"

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("services:area", kwargs={"slug": self.slug})

    @property
    def content_lines(self):
        """Content split into paragraphs for clean template rendering."""
        return [p.strip() for p in (self.content or "").split("\n") if p.strip()]

    @property
    def h1(self):
        """Local headline: «تعمیر پکیج در کرج» — used by template and schema."""
        return f"{self.service.name} در {self.area}"


class ProblemOption(TimeStampedModel):
    """A problem selectable in the request wizard of exactly one Service.

    Like Brand, a problem is meaningless without its service ("آب گرم
    نمی‌شود" belongs to پکیج; a purifier has its own problem list).
    """

    service = models.ForeignKey(
        "content.Service",
        verbose_name="خدمت مربوطه",
        on_delete=models.PROTECT,
        related_name="problems",
        help_text="این مشکل فقط در فرم درخواست همین خدمت نمایش داده می‌شود.",
    )
    label = models.CharField("عنوان مشکل", max_length=120)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)
    active = models.BooleanField("فعال", default=True)

    class Meta:
        verbose_name = "گزینه مشکل"
        verbose_name_plural = "گزینه‌های مشکل"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.label


class HomePageItem(TimeStampedModel):
    """One card in a homepage row: either a "چرا ما" benefit or a work step.

    Rows are edited as simple lists in the admin (add/remove/reorder) instead
    of raw JSON, so a non-technical operator cannot break the homepage.
    """

    class Kind(models.TextChoices):
        BENEFIT = "benefit", "مزیت (چرا ما)"
        STEP = "step", "مرحله کار"

    home = models.ForeignKey(
        "content.HomePageContent",
        verbose_name="صفحه اصلی",
        on_delete=models.CASCADE,
        related_name="items",
    )
    kind = models.CharField("نوع", max_length=10, choices=Kind.choices)
    title = models.CharField("عنوان", max_length=120)
    description = models.TextField("توضیح", blank=True, default="")
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "آیتم صفحه اصلی"
        verbose_name_plural = "آیتم‌های صفحه اصلی"
        ordering = ["kind", "sort_order", "id"]

    def __str__(self):
        return f"{self.get_kind_display()}: {self.title}"


class HomePageContent(TimeStampedModel):
    """CMS-managed copy for homepage sections."""

    hero_title = models.CharField("عنوان اصلی", max_length=200, default="تعمیر تخصصی پکیج در تهران")
    hero_description = models.TextField("توضیح بخش اصلی", default="سریع، مطمئن و منصفانه.")
    hero_cta_label = models.CharField("متن دکمه اصلی", max_length=80, default="ثبت درخواست تعمیر")
    hero_cta_secondary_label = models.CharField("متن دکمه دوم", max_length=80, default="تماس با تعمیرکار")

    services_title = models.CharField("عنوان بخش خدمات", max_length=120, default="خدمات ما")
    services_description = models.TextField("توضیح بخش خدمات", blank=True, default="")

    brands_title = models.CharField("عنوان بخش برندها", max_length=120, default="برندهای تحت سرویس")

    benefits_title = models.CharField("عنوان مزایا", max_length=120, default="چرا اوستا سرویس؟")

    steps_title = models.CharField("عنوان مراحل", max_length=120, default="مراحل کار")

    @property
    def benefits(self):
        """Benefit rows, replacing the old raw-JSON field."""
        return self.items.filter(kind=HomePageItem.Kind.BENEFIT).order_by("sort_order", "id")

    @property
    def steps(self):
        """Step rows, replacing the old raw-JSON field."""
        return self.items.filter(kind=HomePageItem.Kind.STEP).order_by("sort_order", "id")

    faq_title = models.CharField("عنوان پرسش‌های متداول", max_length=120, default="پرسش‌های متداول")

    cta_title = models.CharField("عنوان بخش فراخوان", max_length=160, default="پکیج‌تان نیاز به تعمیر دارد؟")
    cta_description = models.TextField("توضیح فراخوان", blank=True, default="")
    cta_button_label = models.CharField("متن دکمه فراخوان", max_length=80, default="ثبت درخواست تعمیر")

    class Meta:
        verbose_name = "محتوای صفحه اصلی"
        verbose_name_plural = "محتوای صفحه اصلی"


class AboutPageContent(TimeStampedModel):
    """CMS-managed about page content."""

    title = models.CharField("عنوان", max_length=200, default="درباره اوستا سرویس")
    intro = models.TextField("مقدمه", blank=True, default="")
    body = models.TextField("متن صفحه", blank=True, default="")
    image = models.FileField("تصویر", upload_to="about/%Y/%m/", blank=True)

    class Meta:
        verbose_name = "محتوای درباره ما"
        verbose_name_plural = "محتوای درباره ما"

    @property
    def body_lines(self):
        """Body split into paragraphs for clean template rendering."""
        return [p.strip() for p in (self.body or "").split("\n") if p.strip()]


class ContactPageContent(TimeStampedModel):
    """Editable contact page intro (phone/hours/address come from SiteSettings)."""

    title = models.CharField("عنوان", max_length=200, default="تماس با ما")
    intro = models.TextField("مقدمه", blank=True, default="")

    class Meta:
        verbose_name = "محتوای تماس"
        verbose_name_plural = "محتوای تماس"


def _article_image_upload_to(instance, filename):
    return f"articles/{instance.slug or 'draft'}/{filename}"


class Article(SlugAutoMixin, TimeStampedModel, SEOMixin):
    """Troubleshooting / guide article (e.g. common boiler errors).

    Optionally linked to a Service so its CTA preselects that service in the
    request wizard, and shown on the service page's "دقیق‌تر عیب‌یابی" hub.
    """

    slug_source = "title"

    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField(
        "اسلاگ (آدرس صفحه)",
        max_length=200,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خالی بگذارید تا خودکار از عنوان ساخته شود.",
    )
    summary = models.TextField("خلاصه (زیرعنوان فهرست)", blank=True, default="")
    content = models.TextField("متن مقاله", blank=True, default="", help_text="هر پاراگراف در یک خط؛ خط‌های اول هر بلوک به‌صورت تیتر نمایش داده می‌شوند اگر با ## شروع شوند.")
    image = models.FileField("تصویر شاخص", upload_to=_article_image_upload_to, blank=True)
    service = models.ForeignKey(
        "content.Service",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name="articles",
        verbose_name="خدمت مرتبط",
        help_text="CTA ثبت درخواستِ مقاله این خدمت را در فرم از پیش انتخاب می‌کند.",
    )
    published = models.BooleanField("منتشر شده", default=True)

    class Meta:
        verbose_name = "مقاله"
        verbose_name_plural = "مقالات"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("content:article_detail", kwargs={"slug": self.slug})

    @property
    def content_lines(self):
        """Content split into paragraphs for clean template rendering."""
        return [p.strip() for p in (self.content or "").split("\n") if p.strip()]


class FAQ(TimeStampedModel):
    """CMS-managed FAQ shown on /faq/ and the homepage."""

    question = models.CharField("پرسش", max_length=250)
    answer = models.TextField("پاسخ")
    active = models.BooleanField("فعال", default=True)
    sort_order = models.PositiveIntegerField("ترتیب", default=0)

    class Meta:
        verbose_name = "پرسش متداول"
        verbose_name_plural = "پرسش‌های متداول"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.question


class Page(SlugAutoMixin, TimeStampedModel, SEOMixin):
    """Generic informational page for future content."""

    slug_source = "title"

    title = models.CharField("عنوان", max_length=200)
    slug = models.SlugField(
        "اسلاگ (آدرس صفحه)",
        max_length=200,
        unique=True,
        allow_unicode=True,
        blank=True,
        help_text="خالی بگذارید تا خودکار از عنوان ساخته شود.",
    )
    content = models.TextField("محتوا", blank=True, default="")
    published = models.BooleanField("منتشر شده", default=True)

    class Meta:
        verbose_name = "صفحه"
        verbose_name_plural = "صفحات"

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("content:page", kwargs={"slug": self.slug})

    @property
    def content_lines(self):
        """Content split into paragraphs for clean template rendering."""
        return [p.strip() for p in (self.content or "").split("\n") if p.strip()]
