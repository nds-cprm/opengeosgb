from django_recaptcha.fields import ReCaptchaField
from allauth.account.forms import LoginForm


class RecaptchaLoginForm(LoginForm):
    captcha = ReCaptchaField(
        label = ""
    )

    def login(self, *args, **kwargs):
        return super(RecaptchaLoginForm, self).login(*args, **kwargs)
