from django import template
from django.utils.html import mark_safe
register = template.Library()

@register.simple_tag(takes_context=True)
def rendered_answer(context, answer):
    return mark_safe(answer.get_html_repr(context))
