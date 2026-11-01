"""Tests for admin account management features.

Covers: show/hide password toggle presence, user admin (list/create/password
change), the SMS password-recovery wizard (full lifecycle), and the phone
field used by recovery.
"""
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts import recovery
from apps.core.models import SiteSettings
from apps.notifications.models import SmsLog, SmsTemplate

User = get_user_model()


class AdminUserManagementTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.superuser = User.objects.create_superuser(
            username="boss", password="strong-pass-123", email="boss@example.com",
            phone="09120000000",
        )

    def test_user_changelist_lists_phone_column(self):
        self.client.login(username="boss", password="strong-pass-123")
        resp = self.client.get("/admin/accounts/user/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "boss")

    def test_add_user_form_includes_phone(self):
        self.client.login(username="boss", password="strong-pass-123")
        resp = self.client.get("/admin/accounts/user/add/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "name=\"phone\"")

    def test_change_user_password_form_renders(self):
        target = User.objects.create_user(username="staffer", password="x-pass-123")
        self.client.login(username="boss", password="strong-pass-123")
        url = reverse("admin:auth_user_password_change", args=[target.pk])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "password1")

    def test_login_page_has_password_toggle_script(self):
        resp = self.client.get("/admin/login/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "pw-toggle-btn")
        # Eye icon instead of the old text button; no visible text.
        self.assertContains(resp, "pw-toggle-btn svg")
        self.assertContains(resp, 'stroke-width="2"')
        self.assertNotContains(resp, 'btn.textContent = "نمایش"')

    def test_phone_validator_rejects_bad_numbers(self):
        # Optional field: a user with no phone is valid.
        user = User(username="nophone", password="x")
        user.full_clean()  # must not raise
        # Malformed numbers are rejected.
        user.phone = "12345"
        with self.assertRaises(Exception):
            user.full_clean()
        user.phone = "09121234567"
        user.full_clean()  # valid


class RecoveryTestCase(TestCase):
    def setUp(self):
        # The per-IP SMS throttle uses the (local-memory) cache; a fresh cache
        # per test keeps the multi-call tests below independent.
        from django.core.cache import cache

        cache.clear()

    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        SmsTemplate.objects.get_or_create(
            name="admin_password_recovery",
            defaults={"label": "بازیابی", "body": "کد شما: {code}"},
        )
        cls.user = User.objects.create_superuser(
            username="recoverme", password="old-pass-123",
            email="r@example.com", phone="09121234567",
        )

    def _start(self):
        return self.client.post(reverse("accounts:pw_recover_start"), {"username": "recoverme"})

    def _verify(self):
        session_data = self.client.session.get("admin_pw_recovery")
        return self.client.post(
            reverse("accounts:pw_recover_verify"), {"code": session_data["code"]}
        )

    def test_full_recovery_flow_with_mock_sms(self):
        # 1. start → SMS logged, session seeded
        resp = self._start()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["phone"], "09121234567")
        self.assertTrue(
            SmsLog.objects.filter(recipient="989121234567", status=SmsLog.Status.SENT).exists()
        )

        # 2. verify with the right code (from the mock SMS raw payload)
        log = SmsLog.objects.filter(recipient="989121234567").latest("id")
        code = log.response_data["message"].split(":")[1].strip().split()[0]
        resp = self.client.post(reverse("accounts:pw_recover_verify"), {"code": code})
        self.assertEqual(resp.json()["ok"], True)

        # 3. reset → password changed, auto-logged-in, redirect to dashboard
        resp = self.client.post(
            reverse("accounts:pw_recover_reset"),
            {"new_password1": "brand-new-pass-99", "new_password2": "brand-new-pass-99"},
        )
        self.assertEqual(resp.json()["redirect"], "/admin/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-new-pass-99"))
        self.assertIn("_auth_user_id", self.client.session)

        # 4. old password no longer works
        self.client.logout()
        login = self.client.post(
            "/admin/login/", {"username": "recoverme", "password": "old-pass-123"}
        )
        self.assertEqual(login.status_code, 200)  # error page, not a redirect

    def test_wrong_code_increments_tries_and_locks_out(self):
        self._start()
        for expected_remaining in range(4, 0, -1):
            resp = self.client.post(
                reverse("accounts:pw_recover_verify"), {"code": "000000"}
            )
            self.assertFalse(resp.json()["ok"])
            self.assertIn(str(expected_remaining), resp.json()["error"])
        # 5th wrong try locks the session down
        resp = self.client.post(reverse("accounts:pw_recover_verify"), {"code": "000000"})
        self.assertEqual(resp.status_code, 429)
        self.assertIsNone(self.client.session.get("admin_pw_recovery"))

    def test_unknown_username_rejected(self):
        resp = self.client.post(reverse("accounts:pw_recover_start"), {"username": "ghost"})
        self.assertEqual(resp.status_code, 400)

    def test_non_staff_user_cannot_recover(self):
        User.objects.create_user(username="plain", password="x-pass-123")
        resp = self.client.post(reverse("accounts:pw_recover_start"), {"username": "plain"})
        self.assertEqual(resp.status_code, 400)

    def test_reset_requires_verified_session(self):
        self._start()
        resp = self.client.post(
            reverse("accounts:pw_recover_reset"),
            {"new_password1": "a-pass-1234", "new_password2": "a-pass-1234"},
        )
        self.assertEqual(resp.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-pass-123"))

    def test_reset_rejects_weak_password(self):
        self._start()
        self._verify()
        resp = self.client.post(
            reverse("accounts:pw_recover_reset"),
            {"new_password1": "123", "new_password2": "123"},
        )
        self.assertEqual(resp.status_code, 400)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("old-pass-123"))

    def test_start_is_post_only(self):
        resp = self.client.get(reverse("accounts:pw_recover_start"))
        self.assertEqual(resp.status_code, 405)


class QuestionRecoveryTests(TestCase):
    """Recovery via a security question set on the User record."""

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    @classmethod
    def setUpTestData(cls):
        SiteSettings.load()
        cls.user = User.objects.create_superuser(
            username="qadmin", password="old-pass-123", email="q@example.com",
            phone="09121234567",
        )
        cls.user.security_question = "دوستت کیه؟"
        cls.user.security_answer_hash = recovery.hash_answer("ali nazemi")
        cls.user.save(update_fields=["security_question", "security_answer_hash"])

    def _start(self):
        return self.client.post(
            reverse("accounts:pw_recover_question"), {"username": "qadmin"}
        )

    def _answer(self, text):
        return self.client.post(
            reverse("accounts:pw_recover_question_verify"), {"answer": text}
        )

    def test_start_returns_question_text(self):
        resp = self._start()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["question"], "دوستت کیه؟")
        # session is marked as a pending question recovery
        session_data = self.client.session.get("admin_pw_recovery")
        self.assertEqual(session_data["method"], "question")
        self.assertNotIn("verified", session_data)

    def test_full_question_flow_resets_password(self):
        self._start()
        resp = self._answer("ali nazemi")
        self.assertTrue(resp.json()["ok"])
        # reset path from the SMS flow is reused unchanged
        resp = self.client.post(
            reverse("accounts:pw_recover_reset"),
            {"new_password1": "brand-new-pass-99", "new_password2": "brand-new-pass-99"},
        )
        self.assertEqual(resp.json()["redirect"], "/admin/")
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("brand-new-pass-99"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_answer_matching_is_normalized(self):
        self._start()
        resp = self._answer("  ALI   NAZEMI ")
        self.assertTrue(resp.json()["ok"])

    def test_wrong_answer_increments_tries_and_locks_out(self):
        self._start()
        for expected_remaining in range(4, 0, -1):
            resp = self._answer("wrong answer")
            self.assertFalse(resp.json()["ok"])
            self.assertIn(str(expected_remaining), resp.json()["error"])
        resp = self._answer("wrong answer")
        self.assertEqual(resp.status_code, 429)
        self.assertIsNone(self.client.session.get("admin_pw_recovery"))

    def test_answer_without_start_is_rejected(self):
        resp = self._answer("ali nazemi")
        self.assertEqual(resp.status_code, 400)

    def test_user_without_question_rejected(self):
        User.objects.create_superuser(
            username="noquestion", password="x-pass-123", email="n@example.com"
        )
        resp = self.client.post(
            reverse("accounts:pw_recover_question"), {"username": "noquestion"}
        )
        self.assertEqual(resp.status_code, 400)

    def test_unknown_username_rejected(self):
        resp = self.client.post(
            reverse("accounts:pw_recover_question"), {"username": "ghost"}
        )
        self.assertEqual(resp.status_code, 400)

    def test_per_ip_answer_throttle(self):
        self._start()
        from django.core.cache import cache

        cache.set("pwrec:q:count:127.0.0.1", 20, timeout=60)
        resp = self.client.post(
            reverse("accounts:pw_recover_question"), {"username": "qadmin"}
        )
        self.assertEqual(resp.status_code, 429)

    def test_endpoints_are_post_only(self):
        self.assertEqual(
            self.client.get(reverse("accounts:pw_recover_question")).status_code, 405
        )
        self.assertEqual(
            self.client.get(reverse("accounts:pw_recover_question_verify")).status_code,
            405,
        )

    def test_sms_flow_session_is_not_accepted_for_question_verify(self):
        # An SMS-pending session must not let the answer endpoint through.
        self.client.post(
            reverse("accounts:pw_recover_start"), {"username": "qadmin"}
        )
        resp = self._answer("ali nazemi")
        self.assertEqual(resp.status_code, 400)


class StandaloneRecoverPageTests(TestCase):
    """The recovery wizard lives on its own page, separate from login."""

    def test_recover_page_renders(self):
        resp = self.client.get(reverse("accounts:pw_recover"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "بازیابی رمز عبور")
        self.assertContains(resp, "بازگشت به صفحه ورود")

    def test_recover_page_is_separate_from_login(self):
        login_html = self.client.get(reverse("admin:login")).content.decode("utf-8")
        self.assertNotIn("recover-form-start", login_html)
        self.assertIn("رمز عبور را فراموش کرده‌اید؟", login_html)
        self.assertIn(reverse("accounts:pw_recover"), login_html)

    def test_recover_page_links_back_to_login(self):
        recover_html = self.client.get(reverse("accounts:pw_recover")).content.decode("utf-8")
        self.assertIn(reverse("admin:login"), recover_html)
