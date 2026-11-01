"""Set the security question used by /admin/pw-recover/ recovery.

Interactive only: prompts for username, question and answer so the answer
never appears in code, docs, command history or logs. The answer is stored
as a Django password hash on User.security_answer_hash via
apps.accounts.recovery.hash_answer.

Usage:
  python manage.py set_security_question
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.recovery import hash_answer


class Command(BaseCommand):
    help = (
        "سوال امنیتی بازیابی رمز عبور ادمین را تنظیم می‌کند "
        "(پاسخ فقط به‌صورت هش ذخیره می‌شود)."
    )

    def handle(self, *args, **options):
        try:
            username = input("نام کاربری: ").strip()
            question = input("متن سوال (مثلاً: دوستت کیه؟): ").strip()
            answer = input("پاسخ دقیق سوال: ")
        except EOFError:
            raise CommandError("ورودی ناکافی؛ دستور باید تعاملی اجرا شود.")

        if not username or not question or not answer.strip():
            raise CommandError("نام کاربری، سوال و پاسخ نمی‌توانند خالی باشند.")

        User = get_user_model()
        user = User.objects.filter(username__iexact=username).first()
        if user is None:
            raise CommandError(f"کاربری با نام کاربری «{username}» پیدا نشد.")
        if not (user.is_active and user.is_staff):
            raise CommandError("این کاربر ادمین فعال نیست؛ بازیابی برای او کار نمی‌کند.")

        user.security_question = question
        user.security_answer_hash = hash_answer(answer)
        user.save(update_fields=["security_question", "security_answer_hash"])

        self.stdout.write(self.style.SUCCESS(
            f"سوال امنیتی برای «{user.username}» ثبت شد "
            "(پاسخ فقط به‌صورت هش ذخیره شده است)."
        ))
