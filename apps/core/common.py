"""Shared abstract model mixins."""
import re
import unicodedata

from django.db import models
from django.utils.text import slugify



def _brand_fallback_slug():
    """Stable slug token from the business name (imported lazily to avoid a
    circular import: SiteSettings' app imports nothing from common at module
    scope, but keep this safe for any future coupling)."""
    from apps.core.models import SiteSettings

    settings = SiteSettings.objects.first()
    brand = "amozi"
    if settings is not None:
        brand = (
            slugify(
                (settings.business_name or "").replace("\u200c", " "),
                allow_unicode=True,
            )
            or "amozi"
        )
    return f"{brand}-servis"


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField("ایجاد", auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField("به‌روزرسانی", auto_now=True)

    class Meta:
        abstract = True


class SlugAutoMixin(models.Model):
    """Models with a ``slug`` that must never be blank and always unique.

    ``save()`` fills an empty slug from ``slug_source`` so Persian titles typed
    in the admin become valid URLs even though Django's URLify only handles
    Latin characters (the admin's JS prepopulation writes nothing for Persian).
    The source field itself is *not* forced unique — managers edit titles
    freely; duplicates disambiguate with ``-2``, ``-3``, …
    """

    slug_source = "name"
    slug_parts = ()

    class Meta:
        abstract = True

    def _base_slug(self):
        # Models may compose the slug from several fields (e.g. a regional
        # page combines area + service) so identical area names under different
        # services never collide: "کرج" under both services becomes
        # "کرج" and "سرویس-آب-تصفیه‌کن-کرج".
        if self.slug_parts:
            text = ""
            for part in self.slug_parts:
                value = self
                for step in part.split("__"):
                    value = getattr(value, step, "") or ""
                text += str(value) + " "
        else:
            text = str(getattr(self, self.slug_source) or "")
        # Normalise Arabic/Persian variants and strip harakat/ZWNJ noise.
        text = text.replace("\u200c", " ")
        text = text.replace("ي", "ی").replace("ك", "ک").replace("ۀ", "ه")
        text = "".join(ch for ch in text if not unicodedata.category(ch) == "Mn")
        slug = slugify(text, allow_unicode=True)  # keeps Persian letters
        if slug:
            return slug
        # Name itself was blank/punctuation-only: fall back to a stable token.
        return _brand_fallback_slug()

    def _unique_slug(self, base):
        Model = type(self)
        qs = Model.objects.exclude(pk=self.pk)
        if not qs.filter(slug=base).exists():
            return base
        n = 2
        while qs.filter(slug=f"{base}-{n}").exists():
            n += 1
        return f"{base}-{n}"

    def save(self, *args, **kwargs):
        if not (self.slug or "").strip():
            self.slug = self._unique_slug(self._base_slug())
        else:
            # Keep a manually entered slug but guarantee uniqueness too.
            self.slug = self._unique_slug(self.slug.strip())
        super().save(*args, **kwargs)


class SEOMixin(models.Model):
    """Optional per-object SEO overrides; falls back to SiteSettings defaults."""

    seo_title = models.CharField("عنوان سئو", max_length=180, blank=True, default="")
    meta_description = models.TextField("توضیح متا", blank=True, default="")
    og_image = models.FileField(
        "تصویر اشتراک‌گذاری",
        upload_to="seo/%Y/%m/",
        blank=True,
    )

    class Meta:
        abstract = True
