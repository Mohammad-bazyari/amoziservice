"""Request wizard tests: full flow, validation, duplicates, uploads, statuses."""
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.content.models import Brand, ProblemOption, Service
from apps.requests.models import (
    RequestImage,
    RequestStatusHistory,
    ServiceRequest,
)

PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


def make_png_bytes():
    """A guaranteed-valid PNG, generated with Pillow."""
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (8, 8), (200, 30, 30)).save(buf, format="PNG")
    return buf.getvalue()


def seed():
    SiteSettings.load()
    from apps.core.management.commands.seed_site import Command

    Command().handle()
    return (
        Service.objects.get(slug="boiler-repair"),
        Brand.objects.get(slug="butane"),
        ProblemOption.objects.get(label="افت فشار دارد", service__slug="boiler-repair"),
    )


class WizardFlowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_dir = tempfile.mkdtemp()
        cls._media_ctx = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_ctx.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_ctx.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        seed()
        cls.svc_pk = str(Service.objects.get(slug="boiler-repair").pk)
        cls.butane_pk = str(Brand.objects.get(slug="butane").pk)
        cls.prob_pk = str(
            ProblemOption.objects.get(label="افت فشار دارد", service__slug="boiler-repair").pk
        )

    def _post_step(self, step, data=None, follow=False):
        payload = {"_step": step}
        if data:
            payload.update(data)
        return self.client.post(
            reverse("requests:step", args=[step]), payload, follow=follow
        )

    def test_full_flow_creates_request(self):
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step(
            "problem",
            {
                "brand_choice": str(Brand.objects.get(slug="butane").pk),
                "problem_choice": str(
                    ProblemOption.objects.get(label="افت فشار دارد", service__slug="boiler-repair").pk
                ),
                "other_brand_name": "",
                "other_problem_label": "",
                "description": "آب گرم ناپایدار است",
            },
        )
        self._post_step(
            "customer",
            {"customer_name": "علی محمدی", "customer_phone": "09121234567"},
        )
        self._post_step(
            "address",
            {
                "province": "تهران",
                "city": "تهران",
                "district": "پونک",
                "address": "خیابان آزادی، کوچه بهار، پلاک ۱۲",
                "plaque": "12",
                "unit": "3",
                "postal_code": "1234567890",
                "address_notes": "",
            },
        )
        resp = self._post_step("images")

        review = self.client.get(reverse("requests:review"))
        self.assertEqual(review.status_code, 200)

        resp = self.client.post(reverse("requests:submit"), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), 1)

        req = ServiceRequest.objects.first()
        self.assertEqual(req.customer_phone, "09121234567")
        self.assertEqual(req.brand.slug, "butane")
        self.assertEqual(req.status, ServiceRequest.Status.NEW)
        self.assertTrue(req.tracking_code.startswith("BR-"))
        self.assertContains(resp, req.tracking_code)

    def test_submit_sends_both_sms_logs(self):
        """Submit E2E: technician + customer SMS logs, both after commit."""
        from apps.notifications.models import SmsLog

        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": self.butane_pk, "problem_choice": self.prob_pk})
        self._post_step("customer", {"customer_name": "علی محمدی", "customer_phone": "09121234567"})
        self._post_step("address", {
            "province": "تهران", "city": "تهران", "district": "پونک",
            "address": "خیابان آزادی، کوچه بهار، پلاک ۱۲",
            "plaque": "12", "unit": "3", "postal_code": "1234567890",
            "address_notes": "",
        })
        self._post_step("images")
        # on_commit hooks only fire in tests via captureOnCommitCallbacks —
        # this also validates the real submit wiring.
        with self.captureOnCommitCallbacks(execute=True):
            resp = self.client.post(reverse("requests:submit"), follow=True)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        logs = SmsLog.objects.all()
        self.assertEqual(logs.count(), 2)  # technician + customer
        recipients = {log.recipient for log in logs}
        self.assertIn("989120832480", recipients)   # technician (SiteSettings default)
        self.assertIn("989121234567", recipients)   # customer

    def test_review_page_requires_completed_steps(self):
        resp = self.client.get(reverse("requests:review"), follow=True)
        self.assertRedirects(resp, reverse("requests:step", args=["service"]))

    def test_invalid_phone_rejected(self):
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": self.butane_pk, "problem_choice": self.prob_pk})
        resp = self._post_step(
            "customer",
            {"customer_name": "تست", "customer_phone": "0912345"},
        )
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertTrue(form.errors)
        self.assertIn("customer_phone", form.errors)

    def test_phone_normalization(self):
        """+98، ‎0098، صفرِ بلعیده‌شده و ارقام فارسی به 09xxxxxxxxx می‌رسند."""
        from apps.requests.phone import normalize_mobile as norm, operator_name as op

        shape = [
            ("+989121234567", "09121234567"),
            ("00989121234567", "09121234567"),
            ("۰۹۱۲۱۲۳۴۵۶۷", "09121234567"),
            ("9121234567", "09121234567"),
            ("+9809121234567", "09121234567"),
            ("989121234567", "09121234567"),
            ("0 912-123-4567", "09121234567"),
            ("0812345678", "0812345678"),  # بی‌اعتبار می‌ماند — صفرِ غیرموبایل جایگزین نمی‌شود
            ("", ""),
        ]
        for raw, want in shape:
            self.assertEqual(norm(raw), want, f"{raw!r} باید نرمال شود به {want!r}")
        self.assertEqual(op("+989121234567"), "همراه اول")
        self.assertEqual(op("۰۹۳۵۱۱۱۲۲۳۳"), "ایرانسل")
        self.assertEqual(op("۰۹۲۱۱۲۳۴۵۶۷"), "رایتل")
        self.assertEqual(op("08123456789"), "")

    def test_phone_alternate_shapes_accepted_and_stored_normalized(self):
        """+98 و ارقام فارسی از ویزارد پذیرفته و به شکل نرمال ذخیره می‌شوند."""
        from apps.requests.forms import StepCustomerForm

        for raw in ("+989121234567", "00989121234567", "۰۹۱۲۱۲۳۴۵۶۷", "9121234567"):
            form = StepCustomerForm(data={"customer_name": "تست", "customer_phone": raw})
            self.assertTrue(form.is_valid(), f"{raw!r} باید معتبر شود: {form.errors}")
            self.assertEqual(form.cleaned_data["customer_phone"], "09121234567")

    def test_required_address(self):
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": self.butane_pk, "problem_choice": self.prob_pk})
        self._post_step("customer", {"customer_name": "تست", "customer_phone": "09121234567"})
        resp = self._post_step("address", {"province": "تهران", "city": "تهران", "address": ""})
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context["form"].errors)

    def test_duplicate_phone_same_brand_within_window_redirects_to_first(self):
        req = ServiceRequest.objects.create(
            service=Service.objects.get(slug="boiler-repair"),
            brand=Brand.objects.get(slug="butane"),
            problem=ProblemOption.objects.get(
                label="افت فشار دارد", service__slug="boiler-repair"
            ),
            customer_name="اولی",
            customer_phone="09121234567",
            address="آدرس اولی",
        )
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": self.butane_pk, "problem_choice": self.prob_pk})
        self._post_step("customer", {"customer_name": "دومی", "customer_phone": "09121234567"})
        self._post_step("address", {"province": "تهران", "city": "تهران", "address": "آدرس دوم", "district": "سعادت‌آباد"})
        self._post_step("images")
        resp = self.client.post(reverse("requests:submit"), follow=True)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertRedirects(resp, reverse("requests:success", args=[req.tracking_code]))

    def test_same_phone_different_brand_is_allowed(self):
        ServiceRequest.objects.create(
            service=Service.objects.get(slug="boiler-repair"),
            brand=Brand.objects.get(slug="butane"),
            problem=ProblemOption.objects.get(
                label="افت فشار دارد", service__slug="boiler-repair"
            ),
            customer_name="اولی",
            customer_phone="09121234567",
            address="آدرس",
        )
        iran_radiator_pk = str(Brand.objects.get(slug="iran-radiator").pk)
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": iran_radiator_pk, "problem_choice": self.prob_pk})
        self._post_step("customer", {"customer_name": "دومی", "customer_phone": "09121234567"})
        self._post_step("address", {"province": "تهران", "city": "تهران", "address": "آدرس دوم"})
        self._post_step("images")
        resp = self.client.post(reverse("requests:submit"), follow=True)
        self.assertEqual(ServiceRequest.objects.count(), 2)

    def test_double_submit_creates_only_one_request(self):
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": self.butane_pk, "problem_choice": self.prob_pk})
        self._post_step("customer", {"customer_name": "تست", "customer_phone": "09121234567"})
        self._post_step("address", {"province": "تهران", "city": "تهران", "address": "آدرس"})
        self._post_step("images")
        resp1 = self.client.post(reverse("requests:submit"))
        resp2 = self.client.post(reverse("requests:submit"))
        self.assertEqual(ServiceRequest.objects.count(), 1)
        self.assertEqual(resp2.status_code, 302)  # redirected away, no second row

    def test_images_step_redirects_to_review_page(self):
        """Regression: after the images step the wizard must land on the
        standalone review URL, not /step/review/ (which 404s)."""
        self._post_step("service", {"service_choice": self.svc_pk})
        self._post_step("problem", {"brand_choice": self.butane_pk, "problem_choice": self.prob_pk})
        self._post_step(
            "customer", {"customer_name": "تست", "customer_phone": "09121234567"}
        )
        self._post_step("address", {"province": "تهران", "city": "تهران", "address": "آدرس"})
        resp = self._post_step("images", follow=True)
        self.assertRedirects(resp, reverse("requests:review"))

    def test_image_upload_happy_path(self):
        self._post_step("service", {"service_choice": self.svc_pk})
        with self.settings(DATA_UPLOAD_MAX_MEMORY_SIZE=10 * 1024 * 1024):
            resp = self.client.post(
                reverse("requests:step", args=["problem"]),
                {
                    "_step": "problem",
                    "brand_choice": self.butane_pk,
                    "problem_choice": self.prob_pk,
                    "images": SimpleUploadedFile("error.png", make_png_bytes(), content_type="image/png"),
                },
            )
            self.assertEqual(resp.status_code, 302)
        self._post_step("customer", {"customer_name": "تست", "customer_phone": "09121234567"})
        self._post_step("address", {"province": "تهران", "city": "تهران", "address": "آدرس"})
        self.client.post(reverse("requests:submit"), follow=True)
        req = ServiceRequest.objects.first()
        self.assertEqual(RequestImage.objects.filter(request=req).count(), 1)
        img = RequestImage.objects.first()
        self.assertEqual(img.content_type, "image/png")
        self.assertTrue(img.image.name.endswith(".png"))

    def test_executable_upload_rejected(self):
        self._post_step("service", {"service_choice": self.svc_pk})
        resp = self.client.post(
            reverse("requests:step", args=["problem"]),
            {
                "_step": "problem",
                "brand_choice": self.butane_pk,
                "problem_choice": self.prob_pk,
                "images": SimpleUploadedFile("virus.exe", b"MZ\x90\x00", content_type="application/x-msdownload"),
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ServiceRequest.objects.count(), 0)
        self.assertEqual(len(self.client.session.get("request_wizard_images", [])), 0)


@override_settings(MEDIA_ROOT=tempfile.mkdtemp())
class RequestModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()

    def test_tracking_code_unique(self):
        codes = set()
        for i in range(30):
            req = ServiceRequest.objects.create(
                service=Service.objects.first(),
                customer_name=f"تست {i}",
                customer_phone=f"0912123456{i % 10}",
                address="آدرس",
            )
            codes.add(req.tracking_code)
        self.assertEqual(len(codes), 30)
        for code in codes:
            self.assertRegex(code, r"^BR-\d{4}$")

    def test_status_history_logged(self):
        req = ServiceRequest.objects.create(
            service=Service.objects.first(),
            customer_name="تست",
            customer_phone="09121234567",
            address="آدرس",
        )
        req.set_status(ServiceRequest.Status.CONTACTED)
        req.set_status(ServiceRequest.Status.CONFIRMED)
        self.assertEqual(req.status_history.count(), 2)
        self.assertEqual(req.status_history.first().to_status, "confirmed")
        # Same status change is a no-op
        req.set_status(ServiceRequest.Status.CONFIRMED)
        self.assertEqual(req.status_history.count(), 2)

    def test_completed_at_set_on_completion(self):
        req = ServiceRequest.objects.create(
            service=Service.objects.first(),
            customer_name="تست",
            customer_phone="09121234567",
            address="آدرس",
        )
        self.assertIsNone(req.completed_at)
        req.set_status(ServiceRequest.Status.COMPLETED)
        req.refresh_from_db()
        self.assertIsNotNone(req.completed_at)


class WizardRedesignTests(TestCase):
    """Service step first, brand merged into the problem step, data retained
    when navigating back/forward (session-backed, no database)."""

    @classmethod
    def setUpTestData(cls):
        seed()
        cls.svc_pk = str(Service.objects.get(slug="boiler-repair").pk)
        cls.butane_pk = str(Brand.objects.get(slug="butane").pk)
        cls.prob_pk = str(
            ProblemOption.objects.get(label="افت فشار دارد", service__slug="boiler-repair").pk
        )

    def test_start_redirects_to_service_step(self):
        resp = self.client.get(reverse("requests:start"))
        self.assertRedirects(resp, reverse("requests:step", args=["service"]))

    def test_service_step_lists_active_services(self):
        resp = self.client.get(reverse("requests:step", args=["service"]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "تعمیر پکیج")

    def test_brand_other_with_name_is_saved(self):
        self.client.post(
            reverse("requests:step", args=["service"]),
            {"_step": "service", "service_choice": self.svc_pk},
        )
        resp = self.client.post(
            reverse("requests:step", args=["problem"]),
            {
                "_step": "problem",
                "brand_choice": "other",
                "other_brand_name": "الجی",
                "problem_choice": self.prob_pk,
            },
        )
        self.assertEqual(resp.status_code, 302)
        store = self.client.session["request_wizard"]["problem"]
        self.assertEqual(store["brand_choice"], "other")
        self.assertEqual(store["other_brand_name"], "الجی")

    def test_brand_other_without_name_is_rejected(self):
        self.client.post(
            reverse("requests:step", args=["service"]),
            {"_step": "service", "service_choice": self.svc_pk},
        )
        resp = self.client.post(
            reverse("requests:step", args=["problem"]),
            {
                "_step": "problem",
                "brand_choice": "other",
                "other_brand_name": "",
                "problem_choice": self.prob_pk,
            },
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("other_brand_name", resp.context["form"].errors)

    def test_data_retained_when_going_back(self):
        self.client.post(
            reverse("requests:step", args=["service"]),
            {"_step": "service", "service_choice": self.svc_pk},
        )
        self.client.post(
            reverse("requests:step", args=["problem"]),
            {"_step": "problem", "brand_choice": self.butane_pk, "problem_choice": self.prob_pk},
        )
        self.client.post(
            reverse("requests:step", args=["customer"]),
            {"_step": "customer", "customer_name": "علی رضایی", "customer_phone": "09121234567"},
        )
        # Walk back to the problem step: choices must still be selected.
        resp = self.client.get(reverse("requests:step", args=["problem"]))
        self.assertEqual(resp.status_code, 200)
        form = resp.context["form"]
        self.assertEqual(form.initial.get("brand_choice"), self.butane_pk)
        self.assertEqual(form.initial.get("problem_choice"), self.prob_pk)
        # And the customer step keeps its data too.
        resp2 = self.client.get(reverse("requests:step", args=["customer"]))
        self.assertEqual(resp2.context["form"].initial.get("customer_name"), "علی رضایی")

    def test_submit_with_other_brand_writes_free_text(self):
        self.client.post(
            reverse("requests:step", args=["service"]),
            {"_step": "service", "service_choice": self.svc_pk},
        )
        self.client.post(
            reverse("requests:step", args=["problem"]),
            {
                "_step": "problem",
                "brand_choice": "other",
                "other_brand_name": "لورچ مدل قدیمی",
                "problem_choice": self.prob_pk,
            },
        )
        self.client.post(
            reverse("requests:step", args=["customer"]),
            {"_step": "customer", "customer_name": "تست", "customer_phone": "09121234567"},
        )
        self.client.post(
            reverse("requests:step", args=["address"]),
            {"_step": "address", "province": "تهران", "city": "تهران", "address": "آدرس"},
        )
        self.client.post(reverse("requests:step", args=["images"]), {"_step": "images"})
        resp = self.client.post(reverse("requests:submit"), follow=True)
        self.assertEqual(ServiceRequest.objects.count(), 1)
        req = ServiceRequest.objects.first()
        self.assertIsNone(req.brand)
        self.assertEqual(req.other_brand_name, "لورچ مدل قدیمی")
        self.assertEqual(req.service.slug, "boiler-repair")


class PerServiceWizardOptionsTests(TestCase):
    """Brands/problems belong to the service: step 2 shows only the chosen
    service's own items and rejects anything from another service."""

    def setUp(self):
        from apps.content.models import Brand, ProblemOption, Service

        self.boiler = Service.objects.create(name="تعمیر پکیج", slug="boiler-repair", active=True)
        self.water = Service.objects.create(name="سرویس آب تصفیه‌کن", slug="water-purifier", active=True)
        self.b1 = Brand.objects.create(name="بوتان", service=self.boiler, active=True)
        self.b2 = Brand.objects.create(name="دلوکس آب", service=self.water, active=True)
        self.p1 = ProblemOption.objects.create(label="گرمایش ندارد", service=self.boiler, active=True)
        self.p2 = ProblemOption.objects.create(label="شن‌ریزی دارد", service=self.water, active=True)

    def _open_problem_step(self, service):
        session = self.client.session
        session["request_wizard"] = {"service": {"service_choice": str(service.pk)}}
        session.save()
        return self.client.get("/request/step/problem/")

    def test_per_service_problems_shown(self):
        resp = self._open_problem_step(self.water)
        self.assertContains(resp, "شن‌ریزی دارد")
        self.assertNotContains(resp, "گرمایش ندارد")
        self.assertContains(resp, "مشکل آب تصفیه‌کن")

    def test_per_service_brands_shown(self):
        resp = self._open_problem_step(self.water)
        self.assertContains(resp, "دلوکس آب")
        self.assertNotContains(resp, "بوتان")

    def test_service_without_items_shows_empty_lists(self):
        fresh = Service.objects.create(name="خدمت خالی", slug="empty", active=True)
        resp = self._open_problem_step(fresh)
        self.assertNotContains(resp, "بوتان")
        self.assertNotContains(resp, "گرمایش ندارد")

    def test_invalid_option_for_other_service_rejected(self):
        session = self.client.session
        session["request_wizard"] = {"service": {"service_choice": str(self.water.pk)}}
        session.save()
        resp = self.client.post(
            "/request/step/problem/",
            {
                "brand_choice": "other",
                "other_brand_name": "آکوا پرو",
                "problem_choice": str(self.p1.pk),  # boiler-only problem
            },
        )
        self.assertEqual(resp.status_code, 200)  # re-render with errors
        self.assertContains(resp, "گزینه انتخابی معتبر نیست")


def _set_wizard_service(client, service):
    session = client.session
    session["request_wizard"] = {"service": {"service_choice": str(service.pk)}}
    session.save()


class UnconfiguredServiceFreeTextTests(TestCase):
    """A service the admin just created (no brands / no problems configured)
    must NOT show lists whose only choice is «سایر»: it falls back to plain
    free-text fields so the customer just types the brand and problem."""

    def setUp(self):
        from apps.content.models import Service

        self.fresh = Service.objects.create(name="سرویس جopoosh", slug="fresh", active=True)

    def _open(self):
        _set_wizard_service(self.client, self.fresh)
        return self.client.get("/request/step/problem/")

    def test_no_brand_select_rendered(self):
        resp = self._open()
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "<select name=\"brand_choice\"")  # no visible list widget
        self.assertContains(resp, "برند جopoosh شما")

    def test_problem_free_text_instead_of_list(self):
        resp = self._open()
        self.assertNotContains(resp, 'type="radio" name="problem_choice"')
        self.assertContains(resp, "مشکل جopoosh")

    def test_submit_with_free_text_creates_valid_step_data(self):
        _set_wizard_service(self.client, self.fresh)
        resp = self.client.post(
            "/request/step/problem/",
            {
                "other_brand_name": "کروس",
                "other_problem_label": "دیسپنسر کار نمی‌کند",
            },
            follow=True,
        )
        self.assertEqual(resp.request["PATH_INFO"], "/request/step/customer/")
        store = self.client.session["request_wizard"]
        self.assertEqual(store["problem"]["brand_choice"], "other")
        self.assertEqual(store["problem"]["other_brand_name"], "کروس")
        self.assertEqual(store["problem"]["other_problem_label"], "دیسپنسر کار نمی‌کند")

    def test_submit_without_text_shows_error(self):
        _set_wizard_service(self.client, self.fresh)
        resp = self.client.post("/request/step/problem/", {})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "نام برند را وارد کنید")
        self.assertContains(resp, "شرح مشکل را وارد کنید")
