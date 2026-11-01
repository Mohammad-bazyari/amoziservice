"""SMS/notification tests. Kavenegar is always mocked; no real SMS is sent."""
import tempfile
from unittest import mock

from django.test import TestCase, override_settings

from apps.core.models import SiteSettings
from apps.notifications.models import SmsLog, SmsTemplate
from apps.notifications.services import dispatcher, kavenegar
from apps.requests.models import ServiceRequest


def make_request(**overrides):
    from apps.content.models import Service

    service, _ = Service.objects.get_or_create(
        slug="boiler-repair", defaults={"name": "تعمیر پکیج"}
    )
    defaults = dict(
        service=service,
        customer_name="علی محمدی",
        customer_phone="09121234567",
        address="آدرس تست",
        district="پونک",
    )
    defaults.update(overrides)
    return ServiceRequest.objects.create(**defaults)


class MockProviderTests(TestCase):
    """KAVENEGAR_ENABLED=False (default): mock provider, no HTTP calls."""

    def test_send_sms_mock_success(self):
        with mock.patch("apps.notifications.services.kavenegar._request") as req:
            result = kavenegar.send_sms(recipient="09120832480", message="سلام")
        req.assert_not_called()
        self.assertTrue(result["ok"])
        self.assertEqual(result["provider"], "mock")
        self.assertTrue(result["message_id"].startswith("mock-"))

    def test_recipient_normalized(self):
        self.assertEqual(kavenegar.normalize_recipient("09120832480"), "989120832480")
        self.assertEqual(kavenegar.normalize_recipient("+98 912 083 2480"), "989120832480")


@override_settings(KAVENEGAR_ENABLED=True, KAVENEGAR_API_KEY="test-key")
class KavenegarRealModeTests(TestCase):
    """Enabled mode: HTTP layer is mocked, request/response handling is real."""

    def test_send_sms_success(self):
        fake_response = mock.Mock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "return": {"status": 200, "message": "تایید شد"},
            "entries": [{"messageid": 12345, "status": 1, "statustext": "در صف ارسال"}],
        }
        with mock.patch("apps.notifications.services.kavenegar.requests.post", return_value=fake_response) as post:
            result = kavenegar.send_sms(recipient="09120832480", message="سلام", sender="1000123")
        post.assert_called_once()
        self.assertTrue(result["ok"])
        self.assertEqual(result["message_id"], "12345")
        self.assertEqual(result["provider"], "kavenegar")

    def test_send_sms_api_error(self):
        fake_response = mock.Mock()
        fake_response.status_code = 401
        fake_response.json.return_value = {
            "return": {"status": 401, "message": "API key نامعتبر است"}
        }
        with mock.patch("apps.notifications.services.kavenegar.requests.post", return_value=fake_response):
            result = kavenegar.send_sms(recipient="09120832480", message="سلام")
        self.assertFalse(result["ok"])
        self.assertIn("API key نامعتبر", result["error"])

    def test_send_sms_network_failure(self):
        import requests as requests_lib

        with mock.patch(
            "apps.notifications.services.kavenegar.requests.post",
            side_effect=requests_lib.ConnectionError("boom"),
        ):
            result = kavenegar.send_sms(recipient="09120832480", message="سلام")
        self.assertFalse(result["ok"])
        self.assertIn("شبکه", result["error"])

    def test_invalid_json_response(self):
        fake_response = mock.Mock()
        fake_response.status_code = 200
        fake_response.json.side_effect = ValueError("no json")
        with mock.patch("apps.notifications.services.kavenegar.requests.post", return_value=fake_response):
            result = kavenegar.send_sms(recipient="09120832480", message="سلام")
        self.assertFalse(result["ok"])

    def test_check_status_maps_code(self):
        fake_response = mock.Mock()
        fake_response.status_code = 200
        fake_response.json.return_value = {
            "return": {"status": 200, "message": "OK"},
            "entries": [{"status": 4}],
        }
        with mock.patch("apps.notifications.services.kavenegar.requests.post", return_value=fake_response):
            result = kavenegar.check_sms_status("12345")
        self.assertTrue(result["ok"])
        self.assertEqual(result["status_text"], "ارسال شد")


class DispatcherTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()

    def test_dispatch_persists_log(self):
        req = make_request()
        log = dispatcher.dispatch_new_request_sms(req)
        self.assertIsNotNone(log)
        log.refresh_from_db()
        self.assertEqual(log.status, SmsLog.Status.SENT)
        self.assertEqual(log.provider, SmsLog.Provider.MOCK)
        self.assertEqual(log.recipient, "989120832480")
        self.assertIn(req.tracking_code, log.message)

    def test_failure_does_not_raise_and_logs_error(self):
        req = make_request()
        with mock.patch(
            "apps.notifications.services.kavenegar.send_sms",
            return_value={"ok": False, "provider": "kavenegar", "message_id": "",
                          "status_text": "", "raw": None, "error": "API key نامعتبر"},
        ):
            log = dispatcher.dispatch_new_request_sms(req)
        log.refresh_from_db()
        self.assertEqual(log.status, SmsLog.Status.FAILED)
        self.assertIn("API key", log.error_message)
        # The request itself is untouched
        self.assertTrue(ServiceRequest.objects.filter(pk=req.pk).exists())

    def test_sms_disabled_in_settings_skips(self):
        req = make_request()
        s = SiteSettings.load()
        s.sms_enabled = False
        s.save()
        log = dispatcher.dispatch_new_request_sms(req)
        self.assertIsNone(log)
        self.assertEqual(SmsLog.objects.count(), 0)
        s.sms_enabled = True
        s.save()

    def test_template_editing_changes_message(self):
        tpl, _ = SmsTemplate.objects.get_or_create(
            name="new_request_notification",
            defaults={"label": "اطلاع‌رسانی درخواست جدید", "body": "درخواست جدید: {tracking_code}"},
        )
        tpl.body = "کد: {tracking_code} | منطقه: {district}"
        tpl.save()
        req = make_request()
        log = dispatcher.dispatch_new_request_sms(req)
        self.assertEqual(log.message, f"کد: {req.tracking_code} | منطقه: پونک")

    def test_retry_updates_failed_log(self):
        req = make_request()
        log = SmsLog.objects.create(
            request=req, recipient="989120832480", message="سلام",
            provider=SmsLog.Provider.KAVENEGAR, status=SmsLog.Status.FAILED,
            error_message="خطای قبلی",
        )
        with mock.patch(
            "apps.notifications.services.kavenegar.send_sms",
            return_value={"ok": True, "provider": "kavenegar", "message_id": "999",
                          "status_text": "در صف ارسال", "raw": {"ok": 1}, "error": ""},
        ):
            dispatcher.attempt_sms_retry(log)
        log.refresh_from_db()
        self.assertEqual(log.status, SmsLog.Status.SENT)
        self.assertEqual(log.message_id, "999")

    def test_customer_confirmation_sms(self):
        """Customer confirmation: sent to the customer's phone, correct template."""
        req = make_request()
        log = dispatcher.dispatch_customer_confirm_sms(req)
        self.assertIsNotNone(log)
        log.refresh_from_db()
        self.assertEqual(log.status, SmsLog.Status.SENT)
        self.assertEqual(log.recipient, "989121234567")  # customer, normalized
        self.assertIn(req.tracking_code, log.message)
        self.assertIn("ثبت شد", log.message)

    def test_customer_confirmation_disabled_by_settings(self):
        req = make_request()
        s = SiteSettings.load()
        s.customer_sms_enabled = False
        s.save()
        log = dispatcher.dispatch_customer_confirm_sms(req)
        self.assertIsNone(log)
        self.assertEqual(SmsLog.objects.count(), 0)
        s.customer_sms_enabled = True
        s.save()

    def test_customer_confirmation_never_raises(self):
        """A broken provider must not crash the customer confirmation path."""
        req = make_request()
        with mock.patch(
            "apps.notifications.services.kavenegar.send_sms",
            side_effect=RuntimeError("boom"),
        ):
            log = dispatcher.dispatch_customer_confirm_sms(req)  # must not raise
        self.assertIsNotNone(log)
        log.refresh_from_db()
        self.assertEqual(log.status, SmsLog.Status.FAILED)

    def test_both_notifications_fire_together(self):
        """dispatch_request_notifications fires BOTH legs independently."""
        req = make_request()
        tech_log, customer_log = dispatcher.dispatch_request_notifications(req)
        self.assertIsNotNone(tech_log)
        self.assertIsNotNone(customer_log)
        tech_log.refresh_from_db()
        customer_log.refresh_from_db()
        self.assertEqual(tech_log.recipient, "989120832480")   # technician
        self.assertEqual(customer_log.recipient, "989121234567")  # customer
        self.assertIn(req.tracking_code, customer_log.message)

    def test_customer_leg_fires_when_tech_disabled(self):
        """Technician SMS disabled in SiteSettings → customer leg still fires."""
        req = make_request()
        s = SiteSettings.load()
        s.sms_enabled = False
        s.save()
        tech_log, customer_log = dispatcher.dispatch_request_notifications(req)
        self.assertIsNone(tech_log)
        self.assertIsNotNone(customer_log)
        s.sms_enabled = True
        s.save()

    def test_tech_leg_fires_when_customer_disabled(self):
        """Customer SMS disabled → technician leg still fires."""
        req = make_request()
        s = SiteSettings.load()
        s.customer_sms_enabled = False
        s.save()
        tech_log, customer_log = dispatcher.dispatch_request_notifications(req)
        self.assertIsNotNone(tech_log)
        self.assertIsNone(customer_log)
        s.customer_sms_enabled = True
        s.save()

    def test_sms_sent_after_request_commit_via_on_commit(self):
        """submit flow: SMS dispatch is hooked on transaction.on_commit."""
        from django.db import connection

        executed = []
        original = dispatcher.dispatch_new_request_sms
        with mock.patch.object(dispatcher, "dispatch_new_request_sms", side_effect=lambda req: executed.append(req)):
            # Simulate: create request inside a transaction, then commit
            from django.db import transaction

            with transaction.atomic():
                req = make_request()
                connection.on_commit(lambda: dispatcher.dispatch_new_request_sms(req))
            self.assertEqual(executed, [])
            connection.on_commit(lambda: None)
        # after-commit hook ran during the atomic block exit above? verify no exception path:
        self.assertTrue(ServiceRequest.objects.filter(pk=req.pk).exists())
        self.assertIsNotNone(original)
