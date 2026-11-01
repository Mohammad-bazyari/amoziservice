"""Seed admin-related defaults: recovery SMS template + admin accounts.

Idempotent: safe to run repeatedly.
  python manage.py seed_admin_accounts
"""
from django.core.management.base import BaseCommand

from apps.accounts.recovery import DEFAULT_RECOVERY_BODY, RECOVERY_TEMPLATE_NAME
from apps.notifications.models import SmsTemplate


class Command(BaseCommand):
    help = "Seed admin recovery SMS template and default admin accounts"

    def add_arguments(self, parser):
        parser.add_argument("--with-defaults", action="store_true",
                            help="Also ensure qa_admin exists (local dev).")

    def handle(self, *args, **options):
        template, created = SmsTemplate.objects.update_or_create(
            name=RECOVERY_TEMPLATE_NAME,
            defaults={
                "label": "بازیابی رمز عبور پنل مدیریت",
                "body": DEFAULT_RECOVERY_BODY,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"SMS template '{template.name}' {'created' if created else 'updated'}."
        ))

        # Primary owner account: always ensured (idempotent — never overwrites
        # an existing password), so a fresh deployment has a working login.
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user, user_created = User.objects.get_or_create(username="mbazyari")
        if user_created:
            user.set_password("mbazyari")
        user.is_staff = True
        user.is_superuser = True
        user.phone = user.phone or "09120832480"
        user.save()
        self.stdout.write(self.style.SUCCESS(
            f"mbazyari {'created' if user_created else 'already exists'}."
        ))

        if options["with_defaults"]:
            user, user_created = User.objects.get_or_create(username="qa_admin")
            if user_created:
                user.set_password("Baradan@1404")
            user.is_staff = True
            user.is_superuser = True
            user.phone = user.phone or "09120832480"
            user.save()
            self.stdout.write(self.style.SUCCESS(
                f"qa_admin {'created' if user_created else 'already exists'}."
            ))
