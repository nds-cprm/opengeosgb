from django import template
from django.utils.safestring import mark_safe

from ..editor import sanitize_html

register = template.Library()


@register.filter
def sanitize_flatpage(html):
    """HTML de flatpage sanitizado (mesmas regras do admin), pronto para exibição."""
    return mark_safe(sanitize_html(html))
