from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models


phone_validator = RegexValidator(
    regex=r"^09\d{9}$",
    message="شماره موبایل باید ۱۱ رقم و با ۰۹ شروع شود.",
)


class User(AbstractUser):
    """Admin/staff user. Customers never have accounts."""

    phone = models.CharField(
        "موبایل",
        max_length=11,
        blank=True,
        default="",
        validators=[phone_validator],
        help_text=(
            "برای بازیابی رمز عبور از طریق پیامک استفاده می‌شود. "
            "مثال: 09121234567"
        ),
    )
    security_question = models.CharField(
        "سوال امنیتی بازیابی",
        max_length=200,
        blank=True,
        default="",
        help_text=(
            "اگر پر باشد، مدیر می‌تواند رمز عبور را با پاسخ این سوال بازیابی کند. "
            "تنظیم با دستور: python manage.py set_security_question"
        ),
    )
    security_answer_hash = models.CharField(
        "هش پاسخ سوال امنیتی",
        max_length=255,
        blank=True,
        default="",
        help_text="فقط هش ذخیره می‌شود؛ پاسخ خام هرگز.",
    )

    class Meta:
        verbose_name = "کاربر"
        verbose_name_plural = "کاربران"

    def __str__(self):
        full = self.get_full_name()
        return full or self.username
