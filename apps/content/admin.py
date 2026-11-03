"""Admin for SiteSettings and all CMS content (Persian)."""
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from apps.core.templatetags.fa import icon_options

from apps.content.models import (
    AboutPageContent,
    Article,
    Brand,
    ContactPageContent,
    FAQ,
    HeroShowcase,
    HomePageContent,
    HomePageItem,
    Page,
    ProblemOption,
    Service,
    ServiceArea,
)
from apps.core.admin_toolbar import ToolbarMixin
from apps.core.models import SiteSettings


@admin.register(SiteSettings)
class SiteSettingsAdmin(ToolbarMixin, admin.ModelAdmin):
    """Singleton settings editor."""

    fieldsets = (
        ("اطلاعات کسب‌وکار", {"fields": ("business_name", "business_phone", "business_email")}),
        ("موقعیت", {"fields": ("province", "city", "address", "working_hours")}),
        ("هویت بصری", {"fields": ("logo", "favicon")}),
        ("شبکه‌های اجتماعی", {"fields": ("whatsapp", "instagram", "telegram")}),
        ("سئوی پیش‌فرض", {"fields": ("default_seo_title", "default_meta_description", "default_og_image")}),
        ("هزینه‌ها", {"fields": ("inspection_fee",), "description": "هزینه عیب‌یابی به تومان؛ در صفحه خدمات و فرم درخواست نمایش داده می‌شود."}),
        ("پیامک", {"fields": ("sms_enabled", "sms_recipient", "customer_sms_enabled"), "description": "پیامک تعمیرکار: اطلاع درخواست جدید. پیامک مشتری: تأیید ثبت با کد پیگیری به خود مشتری."}),
        ("فوتر", {"fields": ("footer_text",)}),
    )

    def has_add_permission(self, request):
        return False  # singleton

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return super().change_view(request, str(self.model.objects.get_or_create(pk=1)[0].pk), extra_context=extra_context)


@admin.register(Brand)
class BrandAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("name", "logo_preview", "service", "slug", "logo_theme", "active", "sort_order", "updated_at")
    list_editable = ("logo_theme", "active", "sort_order")
    list_filter = ("active", "service", "logo_theme")
    search_fields = ("name", "slug")
    autocomplete_fields = ("service",)
    list_per_page = 20
    actions = ("remove_logos",)
    fieldsets = (
        (
            "لوگو",
            {
                "fields": ("image", "logo_theme"),
                "description": (
                    "فایل لوگو را اینجا بارگذاری یا جایگزین کنید (SVG یا PNG با پس‌زمینه شفاف). "
                    "با تیک «پاک کردن» فایل حذف می‌شود. اگر لوگو سفید است، پس‌زمینه کارت را «تیره» بگذارید."
                ),
            },
        ),
        ("برند", {"fields": ("name", "service", "slug", "active", "sort_order")}),
        ("محتوا", {"fields": ("short_description", "content"), "description": "هر پاراگراف در یک خط؛ برای تیتر داخلی خط را با ## شروع کنید."}),
        ("سئو", {"fields": ("seo_title", "meta_description", "og_image"), "classes": ("collapse",)}),
    )

    @admin.display(description="لوگو")
    def logo_preview(self, obj):
        """Tiny thumbnail in the changelist so a wrong or missing logo is obvious."""
        if not obj.image:
            return "—"
        return format_html(
            '<img src="{}" alt="{}" style="height:26px;width:auto;max-width:90px;object-fit:contain">',
            obj.image.url,
            f"نشان {obj.name}",
        )

    @admin.action(description="حذف فایل لوگوی برندهای انتخاب‌شده")
    def remove_logos(self, request, queryset):
        """The owner must be able to take a logo away again, not only replace it."""
        removed = 0
        for brand in queryset:
            if not brand.image:
                continue
            brand.image.delete(save=False)
            brand.image = ""
            brand.save(update_fields=["image", "updated_at"])
            removed += 1
        self.message_user(request, f"لوگوی {removed} برند حذف شد.")


class ServiceForm(forms.ModelForm):
    """Replaces the raw lucide-name field with a visual picker."""

    class Meta:
        model = Service
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        icon_field = self.fields.get("icon")
        if icon_field:
            icon_field.widget = forms.HiddenInput(attrs={"id": "id_icon_store", "data-icon-store": ""})
            icon_field.help_text = ""

    class Media:
        css = {"all": ("css/admin-icon-picker.css",)}
        js = ("js/admin-icon-picker.js",)


class ServiceAreaInline(admin.TabularInline):
    """Regional landing pages managed right on the service form."""

    model = ServiceArea
    extra = 0
    fields = ("area", "slug", "intro", "active", "sort_order")
    classes = ("collapse",)
    verbose_name = "منطقه"
    verbose_name_plural = "صفحه‌های منطقه‌ای (سئوی محلی)"


@admin.register(ServiceArea)
class ServiceAreaAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("area", "service", "slug", "active", "sort_order", "updated_at")
    list_editable = ("active", "sort_order")
    list_filter = ("active", "service")
    search_fields = ("area", "slug")
    autocomplete_fields = ("service",)
    list_per_page = 20
    fieldsets = (
        ("منطقه", {"fields": ("service", "area", "slug", "active", "sort_order")}),
        ("محتوا", {"fields": ("intro", "content"), "description": "مقدمه، ۲-۳ جمله زیر تیتر صفحه است. محتوای کامل: هر پاراگراف در یک خط؛ برای تیتر داخلی خط را با ## شروع کنید. خالی بگذارید تا متن پیش‌فرض نمایش داده شود."}),
        ("سئو", {"fields": ("seo_title", "meta_description", "og_image"), "classes": ("collapse",)}),
    )


@admin.register(Service)
class ServiceAdmin(ToolbarMixin, admin.ModelAdmin):
    form = ServiceForm
    inlines = (ServiceAreaInline,)
    list_display = ("name", "slug", "active", "sort_order", "updated_at")
    list_editable = ("active", "sort_order")
    search_fields = ("name", "slug")
    list_per_page = 20
    readonly_fields = ("icon_preview",)
    fieldsets = (
        ("خدمت", {"fields": ("name", "slug", "icon_preview", "icon", "image", "active", "sort_order")}),
        ("محتوا", {"fields": ("short_description", "content"), "description": "هر پاراگراف در یک خط؛ برای تیتر داخلی خط را با ## شروع کنید."}),
        (
            "برندها، مشکل‌ها و مناطق این خدمت",
            {
                "fields": (),
                "description": (
                    "برندها و مشکل‌های این خدمت از بخش‌های «برندها» و «گزینه‌های مشکل» مدیریت می‌شوند؛ "
                    "هر برند و هر مشکل به همین خدمت وصل است و فقط در فرم درخواست همین خدمت نمایش داده می‌شود. "
                    "صفحه‌های منطقه‌ای (مثل «تعمیر پکیج در کرج») همین‌جا در بخش «صفحه‌های منطقه‌ای» اضافه می‌شوند."
                ),
            },
        ),
        ("سئو", {"fields": ("seo_title", "meta_description", "og_image"), "classes": ("collapse",)}),
    )
    search_fields = ("name", "slug")

    @admin.display(description="آیکون (انتخاب کنید)")
    def icon_preview(self, obj):
        selected = obj.icon if obj and obj.pk else "wrench"
        return icon_options(selected)



@admin.register(Article)
class ArticleAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("title", "service", "published", "created_at")
    list_filter = ("published", "service")
    search_fields = ("title", "summary", "content")
    list_per_page = 20
    fieldsets = (
        ("مقاله", {"fields": ("title", "slug", "service", "published")}),
        ("محتوا", {"fields": ("summary", "content", "image"), "description": "هر پاراگراف در یک خط؛ برای تیتر داخلی خط را با ## شروع کنید."}),
        ("سئو", {"fields": ("seo_title", "meta_description", "og_image"), "classes": ("collapse",)}),
    )


@admin.register(ProblemOption)
class ProblemOptionAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("label", "service", "sort_order", "active")
    list_editable = ("sort_order", "active")
    list_filter = ("active", "service")
    search_fields = ("label",)
    autocomplete_fields = ("service",)
    list_per_page = 20


class HomePageItemInline(admin.TabularInline):
    """Benefits & steps as plain rows instead of raw JSON."""

    model = HomePageItem
    extra = 0
    fields = ("kind", "title", "description", "sort_order")
    ordering = ("kind", "sort_order")
    verbose_name = "کارت"
    verbose_name_plural = "کارت‌های مزایا و مراحل کار"


@admin.register(HomePageContent)
class HomePageContentAdmin(ToolbarMixin, admin.ModelAdmin):
    fieldsets = (
        ("بخش اصلی (Hero)", {"fields": ("hero_title", "hero_description", "hero_cta_label", "hero_cta_secondary_label")}),
        ("خدمات", {"fields": ("services_title", "services_description")}),
        ("برندها", {"fields": ("brands_title",)}),
        ("مزایا", {"fields": ("benefits_title",), "description": "کارت‌های «چرا ما» را در جدول پایین اضافه/ویرایش/مرتب کنید."}),
        ("مراحل کار", {"fields": ("steps_title",), "description": "مراحل «از درخواست تا تعمیر» را در جدول پایین اضافه/ویرایش/مرتب کنید."}),
        ("پرسش‌های متداول", {"fields": ("faq_title",)}),
        ("فراخوان پایانی", {"fields": ("cta_title", "cta_description", "cta_button_label")}),
    )
    inlines = (HomePageItemInline,)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return super().change_view(request, str(self.model.objects.get_or_create()[0].pk), extra_context=extra_context)


@admin.register(HeroShowcase)
class HeroShowcaseAdmin(ToolbarMixin, admin.ModelAdmin):
    fieldsets = (
        (
            "سرتیتر و اطلاعات اصلی کارت (عیب‌یابی در محل)",
            {
                "fields": (
                    "badge_text",
                    "badge_subtext",
                    "main_icon",
                    "main_title",
                    "main_description",
                ),
                "description": "اطلاعات بالای کارت شامل نشان وضعیت فعال، آیکون اصلی و متن معرفی خدمات عیب‌یابی در محل.",
            },
        ),
        (
            "دکمه اول (معمولاً افت فشار آب / تست منبع انبساط)",
            {
                "fields": (
                    "button1_title",
                    "button1_subtitle",
                    "button1_icon",
                    "button1_article",
                ),
                "description": "عنوان، زیرعنوان، آیکون و مقاله متصل به دکمه اول.",
            },
        ),
        (
            "دکمه دوم (معمولاً رفع نشتی آب / آب‌بندی اتصالات)",
            {
                "fields": (
                    "button2_title",
                    "button2_subtitle",
                    "button2_icon",
                    "button2_article",
                ),
                "description": "عنوان، زیرعنوان، آیکون و مقاله متصل به دکمه دوم.",
            },
        ),
        (
            "دکمه سوم (معمولاً رفع ارور برد / عیب‌یابی الکترونیک)",
            {
                "fields": (
                    "button3_title",
                    "button3_subtitle",
                    "button3_icon",
                    "button3_article",
                ),
                "description": "عنوان، زیرعنوان، آیکون و مقاله متصل به دکمه سوم.",
            },
        ),
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return super().change_view(
            request,
            str(self.model.objects.get_or_create()[0].pk),
            extra_context=extra_context,
        )


@admin.register(AboutPageContent)
class AboutPageContentAdmin(ToolbarMixin, admin.ModelAdmin):
    fields = ("title", "intro", "body", "image")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return super().change_view(request, str(self.model.objects.get_or_create()[0].pk), extra_context=extra_context)


@admin.register(ContactPageContent)
class ContactPageContentAdmin(ToolbarMixin, admin.ModelAdmin):
    fields = ("title", "intro")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def changelist_view(self, request, extra_context=None):
        return super().change_view(request, str(self.model.objects.get_or_create()[0].pk), extra_context=extra_context)


@admin.register(FAQ)
class FAQAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("question", "active", "sort_order")
    list_editable = ("active", "sort_order")
    search_fields = ("question", "answer")
    list_per_page = 20


@admin.register(Page)
class PageAdmin(ToolbarMixin, admin.ModelAdmin):
    list_display = ("title", "slug", "published", "updated_at")
    list_filter = ("published",)
    search_fields = ("title", "content")
    list_per_page = 20
    fields = ("title", "slug", "content", "published", "seo_title", "meta_description", "og_image")

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "content":
            kwargs["help_text"] = "هر پاراگراف در یک خط؛ برای تیتر داخلی خط را با ## شروع کنید."
        return super().formfield_for_dbfield(db_field, request, **kwargs)
