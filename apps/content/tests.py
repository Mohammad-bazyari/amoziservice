"""Content/CMS tests: FAQ, pages, brands, homepage content."""
import shutil
import tempfile
from pathlib import Path

from django.contrib import admin
from django.contrib.messages.storage.cookie import CookieStorage
from django.core.files.base import ContentFile
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.content.admin import BrandAdmin
from apps.content.models import FAQ, Brand, Page, ServiceArea
from apps.core.models import SiteSettings

# Brand logos are copied into MEDIA_ROOT by the seed command, so the carousel
# tests run against a throwaway media directory instead of the project's.
LOGO_TEST_MEDIA = tempfile.mkdtemp(prefix="brand-logos-")


class ContentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        from apps.core.management.commands.seed_site import Command

        Command().handle()

    def test_published_page_visible(self):
        page = Page.objects.create(title="راهنما", slug="guide", content="متن راهنما")
        resp = self.client.get(page.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "متن راهنما")

    def test_unpublished_page_404(self):
        page = Page.objects.create(title="پیش‌نویس", slug="draft", content="x", published=False)
        resp = self.client.get(page.get_absolute_url())
        self.assertEqual(resp.status_code, 404)

    def test_faq_list_shows_active_only(self):
        FAQ.objects.create(question="پیش‌نویس؟", answer="x", active=False)
        resp = self.client.get(reverse("core:faq"))
        self.assertNotContains(resp, "پیش‌نویس؟")

    def test_homepage_contains_seeded_sections(self):
        resp = self.client.get(reverse("core:home"))
        self.assertContains(resp, "تعمیر تخصصی پکیج در تهران")
        self.assertContains(resp, "بوتان")
        self.assertContains(resp, "چطور درخواست تعمیر ثبت کنم؟")

    def test_homepage_renders_benefit_and_step_rows(self):
        """Benefits/steps are rows now; they must render like the old JSON did."""
        resp = self.client.get(reverse("core:home"))
        self.assertContains(resp, "ثبت درخواست آسان")  # benefit seeded
        self.assertContains(resp, "بررسی درخواست")     # step seeded

    def test_admin_can_add_benefit_and_step_without_json(self):
        """A non-technical admin adds a benefit row and it appears on the site."""
        from apps.content.models import HomePageContent, HomePageItem

        home = HomePageContent.objects.get(pk=1)
        HomePageItem.objects.create(
            home=home, kind=HomePageItem.Kind.BENEFIT,
            title="گارانتی کتبی", description="روی همه تعمیرها.", sort_order=9,
        )
        resp = self.client.get(reverse("core:home"))
        self.assertContains(resp, "گارانتی کتبی")

    def test_homepage_safe_when_no_items(self):
        """Deleting all rows must not break the homepage."""
        from apps.content.models import HomePageItem

        HomePageItem.objects.all().delete()
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)

    def test_icon_options_tag_renders_picker(self):
        """The icon picker renders bundled icons and marks the selected one."""
        from django.template import Context, Template

        template = Template("{% load fa %}{% icon_options 'flame' %}")
        html = template.render(Context())
        self.assertIn("data-icon-picker", html)
        self.assertIn('value="flame" checked', html)
        self.assertIn('data-lucide="droplets"', html)

    def test_brand_ordering(self):
        from apps.content.models import Brand

        names = list(Brand.objects.filter(active=True).values_list("name", flat=True))
        self.assertEqual(names[0], "بوتان")
        self.assertEqual(len(names), 7)


class SlugAutoTests(TestCase):
    """Adding a service/brand/page with a Persian name must never break the site.

    Regression: the admin slug field was required while JS prepopulation cannot
    transliterate Persian, so saving failed with a vague "required" error; and
    a Persian slug matched no URL pattern, 500-ing the homepage.
    """

    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        from apps.core.management.commands.seed_site import Command

        Command().handle()

    def _login_admin(self):
        from apps.accounts.models import User

        admin = User.objects.filter(is_superuser=True).first()
        if admin is None:
            admin = User.objects.create_superuser("t", "t@x.io", "x")
        self.client.force_login(admin)

    def test_persian_service_autoslug_and_url(self):
        from apps.content.models import Service

        s = Service.objects.create(name="سرویس و سرویس‌کاری دوره‌ای پکیج")
        self.assertTrue(s.slug)  # auto-generated from the Persian name
        resp = self.client.get(s.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "سرویس و سرویس‌کاری دوره‌ای")

    def test_homepage_ok_with_second_service(self):
        from apps.content.models import Service

        Service.objects.create(name="سرویس دوره‌ای", short_description="تست")
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "سرویس دوره‌ای")

    def test_duplicate_name_gets_unique_slug(self):
        from apps.content.models import Service

        a = Service.objects.create(name="سرویس ویژه")
        b = Service.objects.create(name="سرویس ویژه")
        self.assertNotEqual(a.slug, b.slug)

    def test_admin_add_service_empty_slug_succeeds(self):
        from apps.content.models import Service

        self._login_admin()
        resp = self.client.post(
            reverse("admin:content_service_add"),
            {
                "name": "سرویس دوره‌ای پکیج",
                "slug": "",
                "icon": "",
                "active": "on",
                "sort_order": "0",
                "short_description": "",
                "content": "",
                "seo_title": "",
                "meta_description": "",
                "og_image": "",
                "areas-TOTAL_FORMS": "0",
                "areas-INITIAL_FORMS": "0",
                "areas-MIN_NUM_FORMS": "0",
                "areas-MAX_NUM_FORMS": "1000",
            },
        )
        self.assertEqual(resp.status_code, 302)  # saved, no validation error
        self.assertTrue(Service.objects.filter(name="سرویس دوره‌ای پکیج").exists())

    def test_service_wizard_still_resolves_primary_service(self):
        from apps.content.models import Service

        Service.objects.create(name="خدمت دوم آزمایشی")
        resp = self.client.get(reverse("requests:start"))
        self.assertEqual(resp.status_code, 302)  # straight to the brand step


class ArticleTests(TestCase):
    """Troubleshooting articles: list, detail, CTA preselect and admin."""

    def setUp(self):
        from apps.content.models import Article, Service

        self.svc = Service.objects.create(name="تعمیر پکیج", slug="boiler-repair", active=True)
        self.article = Article.objects.create(
            title="ارورهای متداول پکیج",
            slug="boiler-error-codes",
            summary="معنی کدهای خطا",
            content="مقدمه مقاله\n## تیتر داخلی\nادامه متن",
            service=self.svc,
        )

    def test_article_list_shows_article(self):
        resp = self.client.get("/articles/")
        self.assertContains(resp, "ارورهای متداول پکیج")

    def test_article_detail_renders_headings_and_cta(self):
        resp = self.client.get("/articles/boiler-error-codes/")
        self.assertContains(resp, "تیتر داخلی")
        self.assertContains(resp, "ثبت درخواست")
        self.assertContains(resp, "?service=")
        self.assertNotContains(resp, "##")

    def test_unpublished_article_is_404(self):
        from apps.content.models import Article

        Article.objects.create(title="پیش‌نویس", slug="draft-one", published=False)
        resp = self.client.get("/articles/draft-one/")
        self.assertEqual(resp.status_code, 404)

    def test_start_preselects_service_from_query(self):
        resp = self.client.get(f"/request/?service={self.svc.pk}")
        self.assertRedirects(resp, "/request/step/problem/")
        session = self.client.session
        self.assertEqual(session["request_wizard"]["service"]["service_choice"], str(self.svc.pk))

    def test_start_ignores_invalid_service(self):
        resp = self.client.get("/request/?service=9999")
        self.assertRedirects(resp, "/request/step/service/")


class ServiceAreaTests(TestCase):
    """Regional landing pages (local SEO) — model, page and schema."""

    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        from apps.core.management.commands.seed_site import Command

        Command().handle()

    def test_seed_created_areas_with_composed_slugs(self):
        karaj = ServiceArea.objects.get(service__slug="boiler-repair", area="کرج")
        self.assertEqual(karaj.slug, "کرج-تعمیر-پکیج")
        # Same area under another service gets its own composed slug — no "-2".
        self.assertFalse(ServiceArea.objects.filter(slug="کرج-2").exists())

    def test_area_page_renders_local_h1_and_schema(self):
        karaj = ServiceArea.objects.get(service__slug="boiler-repair", area="کرج")
        resp = self.client.get(karaj.get_absolute_url())
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "تعمیر پکیج در کرج")
        self.assertContains(resp, '"areaServed"')
        self.assertContains(resp, "بوتان")  # service's brands cross-linked

    def test_inactive_area_is_404(self):
        area = ServiceArea.objects.filter(active=True).first()
        area.active = False
        area.save()
        resp = self.client.get(area.get_absolute_url())
        self.assertEqual(resp.status_code, 404)

    def test_area_in_sitemap(self):
        resp = self.client.get("/sitemap.xml")
        self.assertContains(resp, "/services/area/")

    def test_service_detail_lists_areas(self):
        resp = self.client.get("/services/boiler-repair/")
        self.assertContains(resp, "در مناطق تحت پوشش")
        self.assertContains(resp, "کرج-تعمیر-پکیج".replace("کرج-تعمیر-پکیج", "/services/area/"))


@override_settings(MEDIA_ROOT=LOGO_TEST_MEDIA)
class BrandLogoCarouselTests(TestCase):
    """Every brand has a real logo file in media storage and shows up in the
    homepage carousel with its name printed under the logo."""

    IMAGE_MAGIC = (b"<?xml", b"<svg", b"\x89PNG\r\n\x1a\n", b"\xff\xd8")

    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        from apps.core.management.commands.seed_site import Command

        Command().handle()
        cls.boiler = Brand.objects.get(slug="butane").service

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(LOGO_TEST_MEDIA, ignore_errors=True)

    def _homepage(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        return resp.content.decode()

    def test_every_seeded_brand_has_a_logo_file_in_media_storage(self):
        brands = Brand.objects.all()
        self.assertEqual(brands.count(), 7)
        for brand in brands:
            with self.subTest(brand=brand.name):
                self.assertTrue(brand.image, f"{brand.name} logo is empty")
                path = Path(brand.image.path)
                self.assertTrue(path.exists(), f"{brand.name} logo file missing")
                head = path.read_bytes()[:16].lstrip()
                self.assertTrue(
                    head.startswith(self.IMAGE_MAGIC),
                    f"{brand.name} logo is not an image: {path.name}",
                )

    def test_logo_file_is_served_under_media_url(self):
        brand = Brand.objects.get(slug="baxi")
        self.assertIn("/media/brands/", brand.image.url)

    def test_carousel_prints_the_brand_name_under_every_logo(self):
        html = self._homepage()
        brands = Brand.objects.filter(active=True, service__active=True).exclude(image="")
        self.assertGreaterEqual(brands.count(), 7)
        for brand in brands:
            with self.subTest(brand=brand.name):
                self.assertIn(f'alt="نشان {brand.name}"', html)
                self.assertIn(
                    f'<span class="brand-marquee__name">{brand.name}</span>', html
                )

    def test_white_logo_brand_gets_the_dark_chip(self):
        """ایران رادیاتور's official mark is white-on-transparent, so its card
        must be dark to stay visible."""
        brand = Brand.objects.get(slug="iran-radiator")
        self.assertEqual(brand.logo_theme, "dark")
        html = self._homepage()
        self.assertIn('class="brand-marquee__logo brand-marquee__logo--on-dark"', html)
        # The dark chip is used once per animation group (original + duplicate).
        self.assertEqual(html.count("brand-marquee__logo--on-dark"), 2)

    def test_carousel_is_built_from_the_database_not_a_hardcoded_list(self):
        Brand.objects.create(
            name="برند تازه",
            slug="brand-taze",
            service=self.boiler,
            image="brands/butane.png",
            sort_order=99,
        )
        html = self._homepage()
        self.assertIn("برند تازه", html)
        self.assertIn("<span class=\"brand-marquee__name\">برند تازه</span>", html)

    def test_brand_without_logo_is_skipped(self):
        Brand.objects.create(name="بدون لوگو", slug="no-logo", service=self.boiler, image="")
        html = self._homepage()
        self.assertNotIn("بدون لوگو", html)

    def test_inactive_brand_is_skipped(self):
        brand = Brand.objects.get(slug="lorch")
        brand.active = False
        brand.save(update_fields=["active"])
        html = self._homepage()
        self.assertNotIn("<span class=\"brand-marquee__name\">لورچ</span>", html)

    def test_duplicated_animation_group_is_hidden_from_screen_readers(self):
        html = self._homepage()
        groups = html.count('class="brand-marquee__group"')
        hidden = html.count('class="brand-marquee__group" aria-hidden="true"')
        self.assertEqual(groups, 2)  # two identical groups make the loop seamless
        self.assertEqual(hidden, 1)  # the copy is decoration only
        self.assertIn('tabindex="-1"', html)

    def test_reseed_keeps_a_logo_replaced_in_the_admin(self):
        from apps.core.management.commands.seed_site import Command

        brand = Brand.objects.get(slug="baxi")
        brand.image.save(
            "baxi-custom.svg",
            ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'),
            save=True,
        )
        custom_name = brand.image.name
        self.assertIn("baxi-custom.svg", custom_name)

        Command().handle()
        brand.refresh_from_db()
        self.assertEqual(brand.image.name, custom_name)

    def test_reseed_restores_a_deleted_logo_file(self):
        from apps.core.management.commands.seed_site import Command

        brand = Brand.objects.get(slug="chappee")
        Path(brand.image.path).unlink()
        Command().handle()
        brand.refresh_from_db()
        self.assertTrue(Path(brand.image.path).exists())

    def test_admin_can_upload_replace_and_remove_a_logo(self):
        brand = Brand.objects.get(slug="optima")
        admin_obj = BrandAdmin(Brand, admin.site)

        # upload / replace: the model field accepts a new file
        brand.image.save(
            "optima-new.svg",
            ContentFile(b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"/>'),
            save=True,
        )
        brand.refresh_from_db()
        self.assertIn("optima-new.svg", brand.image.name)

        # remove: the bulk action clears the field and deletes the file
        path = Path(brand.image.path)
        request = RequestFactory().get("/admin/content/brand/")
        setattr(request, "_messages", CookieStorage(request))
        admin_obj.remove_logos(request, Brand.objects.filter(pk=brand.pk))
        brand.refresh_from_db()
        self.assertEqual(brand.image.name, "")
        self.assertFalse(path.exists())
        html = self._homepage()
        self.assertNotIn(f'<span class="brand-marquee__name">{brand.name}</span>', html)

    def test_logo_theme_is_editable_per_brand(self):
        brand = Brand.objects.get(slug="baxi")
        brand.logo_theme = "dark"
        brand.save(update_fields=["logo_theme"])
        html = self._homepage()
        self.assertEqual(html.count("brand-marquee__logo--on-dark"), 4)  # 2 chips x 2 groups
