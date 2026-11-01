# Generated migration: customer confirmation SMS toggle.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_sitesettings_inspection_fee"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="customer_sms_enabled",
            field=models.BooleanField(
                default=True,
                help_text="پس از ثبت درخواست، به خود مشتری هم پیامک تأیید با کد پیگیری ارسال می‌شود.",
                verbose_name="پیامک تأیید به مشتری",
            ),
        ),
    ]
