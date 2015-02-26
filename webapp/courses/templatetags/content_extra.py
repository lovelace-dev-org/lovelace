from django import template

register = template.Library()

# {% content_meta %}
@register.inclusion_tag("courses/content-meta.html", takes_context=True)
def content_meta(context):
    return context
