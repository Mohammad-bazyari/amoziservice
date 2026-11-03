"""Core app tests: settings singleton, public pages, phone centralization."""
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SiteSettings


class SiteSettingsTests(TestCase):
    def test_load_creates_singleton(self):
        self.assertEqual(SiteSettings.objects.count(), 0)
        settings_obj = SiteSettings.load()
        self.assertEqual(SiteSettings.objects.count(), 1)
        self.assertEqual(SiteSettings.load().pk, settings_obj.pk)

    def test_default_business_data(self):
        s = SiteSettings.load()
        self.assertEqual(s.business_name, "آموزی سرویس")
        self.assertEqual(s.business_phone, "09120832480")
        self.assertEqual(s.province, "تهران")

    def test_phone_href_normalizes(self):
        s = SiteSettings.load()
        self.assertEqual(s.phone_href, "tel:+989120832480")


class PublicPageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        from apps.core.management.commands.seed_site import Command

        Command().handle()

    def test_homepage_200_and_contains_phone(self):
        resp = self.client.get(reverse("core:home"))
        self.assertEqual(resp.status_code, 200)
        # tel: link uses international form; displayed digits are Persian.
        self.assertContains(resp, "tel:+989120832480")
        self.assertContains(resp, "۰۹۱۲۰۸۳۲۴۸۰")

    def test_about_contact_faq_200(self):
        for url in ("/about/", "/contact/", "/faq/", "/services/", "/brands/"):
            resp = self.client.get(url)
            self.assertEqual(resp.status_code, 200, url)

    def test_service_detail_200(self):
        resp = self.client.get("/services/boiler-repair/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "تعمیر پکیج")

    def test_brand_detail_200(self):
        resp = self.client.get("/brands/butane/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "بوتان")

    def test_brand_detail_404_when_inactive(self):
        from apps.content.models import Brand

        Brand.objects.filter(slug="butane").update(active=False)
        resp = self.client.get("/brands/butane/")
        self.assertEqual(resp.status_code, 404)

    def test_robots_txt(self):
        resp = self.client.get("/robots.txt")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Disallow: /admin/")

    def test_sitemap_xml(self):
        resp = self.client.get("/sitemap.xml")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "/brands/butane/")
        self.assertContains(resp, "/services/boiler-repair/")
        self.assertNotContains(resp, "/admin/")

    def test_phone_change_propagates_from_settings(self):
        """Changing the phone in SiteSettings updates every public page."""
        s = SiteSettings.load()
        s.business_phone = "09121234567"
        s.save()
        for url in ("/", "/contact/", "/about/"):
            resp = self.client.get(url)
            # tel: links use the +98 international form…
            self.assertContains(resp, "tel:+989121234567", status_code=200)
            # …and the displayed digits are Persian-rendered of the local form.
            self.assertContains(resp, "۰۹۱۲۱۲۳۴۵۶۷", status_code=200)
            self.assertNotContains(resp, "09120832480", status_code=200)


class ContextProcessorTests(TestCase):
    def test_site_settings_in_every_response(self):
        resp = self.client.get("/")
        self.assertIn("site_settings", resp.context)
        self.assertEqual(resp.context["site_settings"].business_name, "آموزی سرویس")


class BusinessRenamePropagationTests(TestCase):
    """Renaming the business in the admin panel must reach every section."""

    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        from apps.core.management.commands.seed_site import Command

        Command().handle()

    def test_rename_propagates_across_cms(self):
        s = SiteSettings.load()
        s.business_name = "تست برند"
        s.save()  # must auto-update CMS rows

        from apps.content.models import AboutPageContent, HomePageContent

        home = HomePageContent.objects.first()
        about = AboutPageContent.objects.first()
        s.refresh_from_db()
        self.assertEqual(s.business_name, "تست برند")
        self.assertIn("تست برند", s.default_seo_title)
        self.assertIn("تست برند", home.benefits_title)
        self.assertIn("تست برند", about.title)
        self.assertIn("تست برند", about.intro)

    def test_homepage_shows_new_name_after_rename(self):
        s = SiteSettings.load()
        s.business_name = "تست برند"
        s.save()
        html = self.client.get("/").content.decode("utf-8")
        self.assertIn("تست برند", html)
        self.assertNotIn("آموزی سرویس", html)

    def test_effective_seo_title_falls_back_to_name(self):
        s = SiteSettings.load()
        s.default_seo_title = ""
        s.save()
        s.refresh_from_db()
        self.assertTrue(s.effective_seo_title.startswith(s.business_name))


class InspectionFeeTests(TestCase):
    """The inspection fee comes from SiteSettings and reaches every surface."""

    def test_seeded_faq_answer_uses_render_placeholder(self):
        from apps.core.management.commands.seed_site import Command as Seed

        Seed().handle()
        from apps.content.models import FAQ

        faq = FAQ.objects.filter(answer__contains="{amount}").first()
        self.assertIsNotNone(faq)

    def test_faq_page_expands_amount_from_settings(self):
        from apps.content.models import FAQ

        FAQ.objects.create(
            question="هزینه تعمیر چقدر است؟", answer="هزینه عیب‌یابی {amount} تومان است"
        )
        s = SiteSettings.load()
        s.inspection_fee = 350000
        s.save()
        resp = self.client.get("/faq/")
        # Persian thousands separator (U+066C), never a Latin comma.
        self.assertContains(resp, "۳۵۰٬۰۰۰")
        self.assertNotContains(resp, "{amount}")

    def test_fee_change_propagates_to_faq_page(self):
        from apps.content.models import FAQ

        FAQ.objects.create(
            question="هزینه تعمیر چقدر است؟", answer="هزینه عیب‌یابی {amount} تومان است"
        )
        s = SiteSettings.load()
        s.inspection_fee = 500000
        s.save()
        resp = self.client.get("/faq/")
        self.assertContains(resp, "۵۰۰٬۰۰۰")


class FeePlaceholderLeakTests(TestCase):
    """The {amount} placeholder must never leak raw into rendered pages."""

    def _seed_fee_faq(self):
        from apps.content.models import FAQ

        FAQ.objects.create(
            question="هزینه تعمیر چقدر است؟", answer="هزینه عیب‌یابی {amount} تومان است"
        )

    def test_no_placeholder_leak_on_faq_page(self):
        self._seed_fee_faq()
        import re

        html = self.client.get("/faq/").content.decode("utf-8")
        self.assertNotIn("{amount}", html)

    def test_no_placeholder_leak_on_home_faq_block_and_jsonld(self):
        self._seed_fee_faq()
        import re

        html = self.client.get("/").content.decode("utf-8")
        self.assertNotIn("{amount}", html)
        self.assertIn("۳۵۰٬۰۰۰", html)

    def test_exact_regex_amount_rendered(self):
        self._seed_fee_faq()
        import re

        html = self.client.get("/faq/").content.decode("utf-8")
        self.assertTrue(re.search(r"۳۵۰٬۰۰۰", html))
        self.assertFalse(re.search(r"\{amount\}", html))
