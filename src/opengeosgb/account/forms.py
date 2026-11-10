from allauth.account.forms import LoginForm, SignupForm
from django.contrib.admin.forms import AdminAuthenticationForm
from geonode.people.forms.recaptcha import AllauthRecaptchaLoginForm, AllauthReCaptchaSignupForm, ReCaptchaField


class GovBRMixin:
    class Media:
        css = {
            'all': ('opengeosgb/css/govbr.min.css',)
        }

# Sem recaptcha
class GovBRLoginForm(GovBRMixin, LoginForm):
    pass

class GovBRSignupForm(GovBRMixin, SignupForm):
    pass


# Com recaptcha
class GovBRReCaptchaLoginForm(GovBRMixin, AllauthRecaptchaLoginForm):
    pass

class GovBRReCaptchaSignupForm(GovBRMixin, AllauthReCaptchaSignupForm):
    pass


# Login do admin do Django, com recaptcha
class AdminReCaptchaAuthenticationForm(AdminAuthenticationForm):
    captcha = ReCaptchaField(label=False)
