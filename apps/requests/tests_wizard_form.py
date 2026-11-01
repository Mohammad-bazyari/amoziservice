"""Accessibility + progressive-enhancement tests for the request wizard.

These cover the behaviour borrowed from the React <Form> component:
a linked error summary, aria wiring on invalid controls, and the declarative
hooks the client-side validator reads (data-pattern / data-required).
"""
from django.test import TestCase
from django.urls import reverse

from apps.content.models import Brand, ProblemOption, Service
from apps.core.models import SiteSettings

STEPS_IN_ORDER = ("service", "problem", "customer", "address", "images")


def seed():
    SiteSettings.load()
    from apps.core.management.commands.seed_site import Command

    Command().handle()


class WizardErrorSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        seed()
        cls.service = Service.objects.get(slug="boiler-repair")
        cls.butane_pk = str(Brand.objects.get(slug="butane").pk)
        cls.problem_pk = str(
            ProblemOption.objects.get(
                label="افت فشار دارد", service__slug="boiler-repair"
            ).pk
        )

    def _advance_to(self, step):
        """Session store with every earlier step filled in, like a real customer."""
        store = {}
        reached = STEPS_IN_ORDER.index(step)
        if reached >= 1:
            store["service"] = {"service_choice": str(self.service.pk)}
        if reached >= 2:
            store["problem"] = {
                "brand_choice": self.butane_pk,
                "problem_choice": self.problem_pk,
                "other_brand_name": "",
                "other_problem_label": "",
                "description": "",
            }
        if reached >= 3:
            store["customer"] = {
                "customer_name": "علی محمدی",
                "customer_phone": "09121234567",
            }
        if reached >= 4:
            store["address"] = {
                "province": "تهران",
                "city": "تهران",
                "district": "پونک",
                "address": "خیابان آزادی، کوچه بهار",
                "plaque": "12",
                "unit": "3",
                "postal_code": "1234567890",
                "address_notes": "",
            }
        session = self.client.session
        session["request_wizard"] = store
        session.save()

    def _open(self, step):
        self._advance_to(step)
        return self.client.get(reverse("requests:step", args=[step]))

    def _post_step(self, step, data=None):
        self._advance_to(step)
        payload = {"_step": step}
        if data:
            payload.update(data)
        return self.client.post(reverse("requests:step", args=[step]), payload)

    # -- linked error summary -------------------------------------------------

    def test_invalid_step_lists_every_error_with_a_link_to_its_field(self):
        resp = self._post_step("customer", {"customer_name": "", "customer_phone": ""})
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn('id="wizard-error-summary"', html)
        self.assertIn('role="alert"', html)
        self.assertIn('aria-labelledby="wizard-error-summary-title"', html)
        self.assertIn("لطفاً این موارد را اصلاح کنید", html)
        # Links jump straight to the offending field…
        self.assertIn('href="#id_customer_name"', html)
        self.assertIn('href="#id_customer_phone"', html)
        # …and each field's message carries the id the link points at.
        self.assertIn('id="id_customer_name-error"', html)
        self.assertIn('id="id_customer_phone-error"', html)

    def test_invalid_control_is_wired_with_aria(self):
        resp = self._post_step("customer", {"customer_name": "علی", "customer_phone": "123"})
        html = resp.content.decode()
        self.assertIn('aria-invalid="true"', html)
        self.assertIn('aria-describedby="id_customer_phone-error"', html)
        # The field that was fine keeps no error state of its own.
        self.assertNotIn('id="id_customer_name-error"', html)

    def test_radio_group_errors_are_linked_and_described(self):
        resp = self._post_step(
            "problem",
            {
                "brand_choice": self.butane_pk,
                "problem_choice": "",
                "other_brand_name": "",
                "other_problem_label": "",
                "description": "",
            },
        )
        html = resp.content.decode()
        self.assertIn('href="#id_problem_choice"', html)
        self.assertIn('id="id_problem_choice-error"', html)
        self.assertIn('aria-describedby="id_problem_choice-error"', html)

    def test_images_error_links_to_the_visible_drop_zone(self):
        # The native file input is visually hidden, so the summary must point at
        # the drop-zone button the customer actually sees.
        resp = self._open("images")
        self.assertContains(resp, 'id="images-dropzone"')

    def test_fresh_step_has_no_error_state(self):
        resp = self._open("customer")
        html = resp.content.decode()
        self.assertNotIn('id="wizard-error-summary"', html)
        self.assertNotIn('aria-invalid="true"', html)
        self.assertNotIn("لطفاً این موارد را اصلاح کنید", html)

    # -- client-side validation hooks ----------------------------------------

    def test_form_is_wired_for_client_side_validation(self):
        resp = self._open("service")
        html = resp.content.decode()
        self.assertIn("data-wizard-form", html)
        self.assertIn("window.WizardForm", html)
        self.assertRegex(html, r"/static/js/wizard-form\.[0-9a-f]+\.js")
        # Choice groups declare their own requiredness (Django disables the
        # native `required` attribute on radio widgets).
        self.assertIn('data-required="true"', html)
        self.assertIn('data-error-label="چه کاری لازم دارید؟"', html)

    def test_phone_rule_is_shared_between_server_and_client(self):
        from apps.requests.forms import PHONE_ERROR, PHONE_PATTERN

        html = self._open("customer").content.decode()
        self.assertIn(f'data-pattern="{PHONE_PATTERN}"', html)
        self.assertIn(f'data-error-pattern="{PHONE_ERROR}"', html)
        # The client hint is built from the very rule the server validates with.
        resp = self._post_step(
            "customer", {"customer_name": "علی", "customer_phone": "0812345678"}
        )
        self.assertContains(resp, PHONE_ERROR)

    def test_postal_code_rule_is_shared_between_server_and_client(self):
        from apps.requests.forms import POSTAL_CODE_ERROR, POSTAL_CODE_PATTERN

        html = self._open("address").content.decode()
        self.assertIn(f'data-pattern="{POSTAL_CODE_PATTERN}"', html)
        self.assertIn(f'data-error-pattern="{POSTAL_CODE_ERROR}"', html)

    def test_server_still_rejects_what_the_client_hints_cannot_catch(self):
        """Client validation is a hint; the server remains authoritative."""
        resp = self._post_step(
            "customer", {"customer_name": "علی", "customer_phone": "08123456789"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "شماره موبایل معتبر نیست")

    def test_valid_step_still_advances(self):
        resp = self._post_step(
            "customer", {"customer_name": "علی محمدی", "customer_phone": "09121234567"}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("requests:step", args=["address"]))
