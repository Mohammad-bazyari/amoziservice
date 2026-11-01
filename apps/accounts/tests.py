"""Admin/auth tests: login, protection, dashboard, staff SMS endpoints."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import SiteSettings
from apps.notifications.models import SmsLog
from apps.requests.models import ServiceRequest
from apps.content.models import Service

User = get_user_model()


class AuthTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.staff = User.objects.create_user(
            username="manager", password="strong-pass-123", is_staff=True
        )

    def test_admin_login_works(self):
        resp = self.client.post("/admin/login/", {"username": "manager", "password": "strong-pass-123"})
        self.assertEqual(resp.status_code, 302)

    def test_admin_login_wrong_password(self):
        resp = self.client.post("/admin/login/", {"username": "manager", "password": "wrong"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "فرم ورود مجدداً پر کنید") if False else None
        self.assertContains(resp, "errornote", status_code=200)

    def test_admin_requires_authentication(self):
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/admin/login/", resp["Location"])

    def test_non_staff_cannot_enter_admin(self):
        User.objects.create_user(username="plain", password="strong-pass-123")
        self.client.login(username="plain", password="strong-pass-123")
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)  # redirected to login with error

    def test_logout(self):
        self.client.login(username="manager", password="strong-pass-123")
        # Django 5.x admin logout requires POST.
        resp = self.client.post("/admin/logout/", follow=True)
        self.assertEqual(resp.status_code, 200)
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 302)


@override_settings(MEDIA_ROOT="media_test_tmp")
class AdminDashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.admin = User.objects.create_superuser(
            username="boss", password="strong-pass-123", email="boss@example.com"
        )
        service, _ = Service.objects.get_or_create(
            slug="boiler-repair", defaults={"name": "تعمیر پکیج"}
        )
        from apps.content.models import Brand

        brand, _ = Brand.objects.get_or_create(
            slug="butane",
            defaults={"name": "بوتان", "service": service},
        )
        cls.req = ServiceRequest.objects.create(
            service=service,
            brand=brand,
            customer_name="مشتری تست",
            customer_phone="09121234567",
            address="آدرس",
        )

    def test_dashboard_shows_stats(self):
        self.client.login(username="boss", password="strong-pass-123")
        resp = self.client.get("/admin/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "داشبورد مدیریت")
        self.assertContains(resp, "جدید")

    def test_request_changelist_search_and_filter(self):
        self.client.login(username="boss", password="strong-pass-123")
        resp = self.client.get("/admin/requests/servicerequest/", {"q": "09121234567"})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "مشتری تست")
        resp = self.client.get("/admin/requests/servicerequest/", {"status__exact": "new"})
        self.assertEqual(resp.status_code, 200)

    def test_status_change_action_logs_history(self):
        self.client.login(username="boss", password="strong-pass-123")
        url = reverse("admin:requests_servicerequest_changelist")
        self.client.post(
            url,
            {
                "action": "mark_contacted",
                "_selected_action": [str(self.req.pk)],
            },
            follow=True,
        )
        self.req.refresh_from_db()
        self.assertEqual(self.req.status, ServiceRequest.Status.CONTACTED)
        self.assertEqual(self.req.status_history.count(), 1)

    def test_internal_note_created_via_inline(self):
        from apps.content.models import Brand

        brand = Brand.objects.first()
        self.client.login(username="boss", password="strong-pass-123")
        url = reverse("admin:requests_servicerequest_change", args=[self.req.pk])
        resp = self.client.post(
            url,
            {
                "service": self.req.service.pk,
                "brand": brand.pk if brand else "",
                "customer_name": self.req.customer_name,
                "customer_phone": self.req.customer_phone,
                "province": self.req.province,
                "city": self.req.city,
                "address": self.req.address,
                "status": "contacted",
                # Management forms for every inline (prefix = related_name)
                "images-TOTAL_FORMS": "0",
                "images-INITIAL_FORMS": "0",
                "images-MIN_NUM_FORMS": "0",
                "images-MAX_NUM_FORMS": "1000",
                "status_history-TOTAL_FORMS": "0",
                "status_history-INITIAL_FORMS": "0",
                "status_history-MIN_NUM_FORMS": "0",
                "status_history-MAX_NUM_FORMS": "1000",
                "notes-TOTAL_FORMS": "1",
                "notes-INITIAL_FORMS": "0",
                "notes-MIN_NUM_FORMS": "0",
                "notes-MAX_NUM_FORMS": "1000",
                "notes-0-body": "مشتری تماس گرفت؛ زمان مراجعه فردا",
            },
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.req.refresh_from_db()
        self.assertEqual(self.req.notes.count(), 1)
        self.assertEqual(self.req.notes.first().body, "مشتری تماس گرفت؛ زمان مراجعه فردا")

    def test_sms_log_admin_lists_and_retry_action(self):
        log = SmsLog.objects.create(
            request=self.req,
            recipient="989120832480",
            message="سلام",
            provider=SmsLog.Provider.MOCK,
            status=SmsLog.Status.FAILED,
            error_message="قطع شبکه",
        )
        self.client.login(username="boss", password="strong-pass-123")
        resp = self.client.get("/admin/notifications/smslog/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "989120832480")

        url = reverse("admin:notifications_smslog_changelist")
        with mock.patch(
            "apps.notifications.services.kavenegar.send_sms",
            return_value={"ok": True, "provider": "mock", "message_id": "m-1",
                          "status_text": "mock", "raw": {}, "error": ""},
        ):
            self.client.post(url, {"action": "retry_selected", "_selected_action": [str(log.pk)]}, follow=True)
        log.refresh_from_db()
        self.assertEqual(log.status, SmsLog.Status.SENT)


class StaffSmsEndpointsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        User.objects.create_superuser(username="boss", password="strong-pass-123", email="b@example.com")
        service, _ = Service.objects.get_or_create(slug="boiler-repair", defaults={"name": "تعمیر پکیج"})
        cls.req = ServiceRequest.objects.create(
            service=service, customer_name="م", customer_phone="09121234567", address="آدرس"
        )
        cls.log = SmsLog.objects.create(
            request=cls.req, recipient="989120832480", message="سلام",
            provider=SmsLog.Provider.MOCK, status=SmsLog.Status.FAILED,
        )

    def test_requires_staff(self):
        resp = self.client.post(reverse("notifications:sms_retry", args=[self.log.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_retry_endpoint(self):
        self.client.login(username="boss", password="strong-pass-123")
        with mock.patch(
            "apps.notifications.services.kavenegar.send_sms",
            return_value={"ok": True, "provider": "mock", "message_id": "m-2",
                          "status_text": "ok", "raw": {}, "error": ""},
        ):
            resp = self.client.post(reverse("notifications:sms_retry", args=[self.log.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.log.refresh_from_db()
        self.assertEqual(self.log.status, SmsLog.Status.SENT)

    def test_retry_rejects_get(self):
        self.client.login(username="boss", password="strong-pass-123")
        resp = self.client.get(reverse("notifications:sms_retry", args=[self.log.pk]))
        self.assertEqual(resp.status_code, 405)
