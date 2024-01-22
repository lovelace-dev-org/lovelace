from django import template

register = template.Library()


# {% tool_links %}
@register.inclusion_tag("teacher_tools/tool_links.html", takes_context=True)
def tool_links(context):
    return context
