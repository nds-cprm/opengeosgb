import re

from django.conf import settings

GTM_REGEX = re.compile(r'^GTM-[A-Z0-9]{4,10}$')


def google_tag_manager_snippet(request):
    gtag = str(getattr(settings, "GOOGLE_TAG_MANAGER_ID", "") or "")

    return {
        "GOOGLE_TAG_MANAGER_ID": gtag if GTM_REGEX.match(gtag) else ""
    }
