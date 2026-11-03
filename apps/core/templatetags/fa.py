"""Template filters: Persian digits and phone formatting."""
import json

from django import template
from datetime import date

from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

# Persian thousands separator (U+066C) — the Latin comma is wrong in Persian text.
_THOUSANDS_SEPARATOR = "٬"


@register.filter(name="fa_digits")
def fa_digits(value):
    """Convert Latin digits to Persian digits."""
    return str(value).translate(_FA_DIGITS)


@register.filter(name="render_text")
def render_text(value):
    """Expand CMS placeholders at render time.

    Currently supported:
      {amount} → the inspection fee formatted as Toman (e.g. ۳۵۰٬۰۰۰).

    Used for FAQ answers stored in the database so that changing the fee in
    the admin panel propagates everywhere without re-seeding.
    """
    text = str(value or "")
    if "{amount}" not in text:
        return text
    from apps.core.models import SiteSettings

    return text.replace(
        "{amount}", toman(SiteSettings.load().inspection_fee)
    )


@register.filter(name="toman")
def toman(value):
    """Format a Toman amount with the Persian thousands separator and digits.

    350000 → ۳۵۰٬۰۰۰
    """
    try:
        amount = int(value or 0)
    except (TypeError, ValueError):
        return value
    return f"{amount:,}".replace(",", _THOUSANDS_SEPARATOR).translate(_FA_DIGITS)


_JALALI_MONTHS = [
    "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند",
]

# Jalali new year reference: 1 Farvardin 1404 == 2025-03-21 (Gregorian).
_JALALI_EPOCH = date(2025, 3, 21)


def _to_jalali(value):
    """Gregorian date/datetime → (jy, jm, jd). Days-difference from epoch;
    month lengths (first 6 = 31, next 5 = 30, Esfand = 29/30) resolved iteratively.
    """
    from datetime import date, datetime, timedelta

    from django.utils import timezone as _dj_tz

    if isinstance(value, datetime):
        # An aware datetime carries UTC unless converted — .date() on the raw
        # value would label a request created after 20:30 Tehran time with
        # the previous Jalali day. Convert to the active (Tehran) zone first.
        if _dj_tz.is_aware(value):
            value = _dj_tz.localtime(value)
        value = value.date()
    if not isinstance(value, date):
        return None
    days = (value - _JALALI_EPOCH).days  # 0 == 1 Farvardin 1404
    if days < 0:  # earlier than the epoch: walk backwards month by month
        jy, jm, jd = 1404, 1, 1
        while days < 0:
            jm -= 1
            if jm == 0:
                jm = 12
                jy -= 1
            days += _jalali_month_len(jy, jm)
        jd = days + 1
        return jy, jm, jd
    jy = 1404
    while True:
        # Consistent with _jalali_month_len: the year whose Esfand has 30
        # days is the leap year itself (not jy + 1).
        year_len = 366 if _is_jalali_leap(jy) else 365
        if days < year_len:
            break
        days -= year_len
        jy += 1
    for jm in range(1, 13):
        mlen = _jalali_month_len(jy, jm)
        if days < mlen:
            return jy, jm, days + 1
        days -= mlen
    return jy, 12, 30  # unreachable safeguard


def _is_jalali_leap(jy):
    """Birashk-style leap test; accurate for the 1178–1633 AP range we serve."""
    return ((jy - 474) % 2820 * 682 + 38) % 2816 < 682


def _jalali_month_len(jy, jm):
    if jm <= 6:
        return 31
    if jm <= 11:
        return 30
    return 30 if _is_jalali_leap(jy) else 29


@register.filter(name="jdate")
def jdate(value, fmt="jd F"):
    """Gregorian date → Jalali (Shamsi) string. fmt tokens: jy, jm, jd, F=month name."""
    parts = _to_jalali(value)
    if parts is None:
        return value
    jy, jm, jd = parts
    out = fmt
    out = out.replace("jy", str(jy)).replace("jm", str(jm))
    out = out.replace("jd", str(jd)).replace("F", _JALALI_MONTHS[jm - 1] if 1 <= jm <= 12 else "")
    return out.translate(_FA_DIGITS)


def _tel_href(phone: str) -> str:
    digits = "".join(ch for ch in str(phone) if ch.isdigit())
    if digits.startswith("0"):
        digits = "+98" + digits[1:]
    return f"tel:{digits}"


@register.filter(name="tel_href")
def tel_href(phone):
    """Filter form: {{ phone|tel_href }} → tel:+98…"""
    return _tel_href(phone)


@register.simple_tag(name="tel_href")
def tel_href_tag(phone):
    """Tag form: {% tel_href site_settings.business_phone %} → tel:+98…"""
    return _tel_href(phone)


@register.inclusion_tag("partials/breadcrumbs.html", takes_context=True)
def breadcrumbs(context, spec):
    """Render breadcrumb navigation + expose it for BreadcrumbList JSON-LD.

    Usage: {% breadcrumbs "صفحه اصلی|/;خدمات|/services/;تعمیر پکیج|" %}
    Items are separated by ";" and each item is "title|url"; an empty url
    marks the current page.

    The parsed items are also stored on the request (request._breadcrumb_items)
    so the ``breadcrumb_jsonld`` tag in the same library can emit a matching
    schema.org/BreadcrumbList without repeating the trail in each template.
    """
    items = []
    for chunk in (spec or "").split(";"):
        chunk = chunk.strip()
        if not chunk:
            continue
        title, _, url = chunk.partition("|")
        items.append({"title": title.strip(), "url": url.strip()})
    request = context.get("request")
    if request is not None:
        setattr(request, "_breadcrumb_items", items)
    return {"breadcrumb_items": items}


@register.simple_tag(takes_context=True)
def breadcrumb_jsonld(context):
    """Emit schema.org/BreadcrumbList from the nearest {% breadcrumbs %} call.

    Silent when no breadcrumb trail was rendered (single-level pages), so it is
    safe to include once in base.html for every page.
    """
    request = context.get("request")
    items = getattr(request, "_breadcrumb_items", None) if request is not None else None
    if not items:
        return ""
    elements = []
    position = 0
    for item in items:
        position += 1
        element = {
            "@type": "ListItem",
            "position": position,
            "name": item["title"],
        }
        if item["url"]:
            element["item"] = context["request"].build_absolute_uri(item["url"])
        elements.append(element)

    payload = json.dumps(
        {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elements},
        ensure_ascii=False,
    )
    # Neutralise any "</script>" breakout from titles while keeping valid JSON.
    payload = payload.replace("<", "\\u003c")
    return format_html('<script type="application/ld+json">{}</script>', mark_safe(payload))


@register.filter
def first_word(value):
    """First space-separated word: "آموزی سرویس" → "آموزی"."""
    return str(value or "").split(" ")[0] if str(value or "").strip() else ""


@register.filter
def rest_words(value):
    """Everything after the first word: "آموزی سرویس" → "سرویس"."""
    parts = str(value or "").split(" ", 1)
    return parts[1] if len(parts) > 1 else ""


@register.simple_tag(takes_context=True)
def page_title(context, fallback):
    return context.get("seo_title") or fallback


@register.simple_tag
def icon_options(selected: str = "", css_class: str = ""):
    """Render the icon-picker grid used in the admin Service form.

    Emits one radio row per bundled icon; the JS in base_site.html previews the
    chosen icon so the operator never has to type a raw lucide name.
    """
    from django.conf import settings

    names = list(getattr(settings, "ADMIN_ICON_CHOICES", ()))
    safe_selected = "".join(ch for ch in str(selected or "") if ch.isalnum() or ch == "-")
    out = ['<div class="b-icon-picker" data-icon-picker>']
    for i, name in enumerate(names):
        checked = "checked" if name == safe_selected else ("checked" if not safe_selected and i == 0 else "")
        out.append(
            f'<label class="b-icon-opt" title="{name}">'
            f'<input type="radio" name="icon_choice" value="{name}" {checked}>'
            f'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            f'stroke-linecap="round" stroke-linejoin="round" data-lucide="{name}" aria-hidden="true"></svg>'
            f"</label>"
        )
    out.append("</div>")
    return mark_safe("".join(out))


@register.simple_tag
def lucide(name: str, css_class: str = "w-5 h-5", stroke_width: float = 2.0):
    """Render an inline Lucide SVG icon by name.

    Usage: {% lucide "wrench" "w-6 h-6 text-brand-600" %}
    The full lucide icon set is bundled in static/js/lucide-icons.js
    which defines window.LUCIDE_ICONS = {name: pathdata}.
    """
    safe_name = "".join(ch for ch in str(name) if ch.isalnum() or ch == "-")
    return mark_safe(
        f'<svg class="{css_class}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="{stroke_width}" stroke-linecap="round" stroke-linejoin="round" '
        f'data-lucide="{safe_name}" aria-hidden="true"></svg>'
    )


@register.filter(name="elided_pages")
def elided_pages(page_obj, on_each_side=1):
    """Return an elided page range (1 ... neighbors ... last) for pagination.

    Usage: {% for p in page_obj|elided_pages %}
    """
    if not page_obj or not hasattr(page_obj, "paginator"):
        return []
    try:
        return list(
            page_obj.paginator.get_elided_page_range(
                number=page_obj.number,
                on_each_side=int(on_each_side or 1),
                on_ends=1,
            )
        )
    except Exception:
        return []

