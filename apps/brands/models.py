from django.db import models

from apps.content.models import Brand


class ProxyBrand(Brand):
    """Backwards-compatibility proxy; the real model lives in apps.content.

    The project consolidated all content-domain models (Brand, Service,
    ProblemOption, CMS content, FAQ, Page) into apps.content.models. This
    proxy keeps historical imports (apps.brands.models.Brand) working so
    existing code and tests do not need churn.
    """

    class Meta:
        proxy = True
        verbose_name = "برند"
        verbose_name_plural = "برندها"
