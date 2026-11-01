"""Forms for the admin password recovery flow (username → SMS code → new password)."""
from django import forms
from django.contrib.auth import get_user_model, password_validation

from apps.accounts.recovery import find_recoverable_user


class RecoverUsernameForm(forms.Form):
    username = forms.CharField(
        label="نام کاربری",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "username", "autofocus": True}),
    )

    def clean_username(self) -> str:
        username = self.cleaned_data["username"].strip()
        if find_recoverable_user(username) is None:
            raise forms.ValidationError(
                "کاربری با این نام کاربری پیدا نشد (یا اکانت غیرفعال است)."
            )
        return username


class RecoverCodeForm(forms.Form):
    code = forms.CharField(
        label="کد بازیابی",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={"inputmode": "numeric", "autocomplete": "one-time-code", "autofocus": True}
        ),
    )

    def clean_code(self) -> str:
        code = self.cleaned_data["code"]
        if not code.isdigit():
            raise forms.ValidationError("کد فقط باید شامل رقم باشد.")
        return code


class RecoverPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label="رمز عبور جدید",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text=password_validation.password_validators_help_text_html(),
    )
    new_password2 = forms.CharField(
        label="تکرار رمز عبور جدید",
        strip=False,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_new_password2(self) -> str:
        password1 = self.cleaned_data.get("new_password1")
        password2 = self.cleaned_data.get("new_password2")
        if password1 and password1 != password2:
            raise forms.ValidationError("دو رمز وارد شده یکسان نیستند.")
        return password2
