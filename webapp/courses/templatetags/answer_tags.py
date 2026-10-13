from django import template
from django.utils.html import mark_safe
register = template.Library()

@register.simple_tag(takes_context=True)
def rendered_answer(context, answer):
    return mark_safe(answer.get_html_repr(context))

@register.inclusion_tag("courses/answer-action-options.html", takes_context=True)
def answer_actions_extra(context, content_data, answer):
    return {
        "action_options": content_data.get_answer_actions_extra(content_data, context, answer),
        "content": content_data,
        "answer": answer,
    }
