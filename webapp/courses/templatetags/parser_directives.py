from django import template

from courses.models import ContentPage
from courses.content_parser import MarkupParser

register = template.Library()

# TODO: This allows code injection via admin. Not good.

# {% embedded_calendar "calendar_name" %}
@register.simple_tag
def embedded_calendar(calendar_name):
    return ""

# {% embedded_page "page-slug" %}
@register.inclusion_tag("courses/task.html")
def embedded_page(page_slug):
    # TODO: Recursion for embedded items in embedded pages
    embedded_content = ContentPage.objects.get(slug=page_slug)
    emb_content = ""
    for line in MarkupParser.parse(embedded_content.content):
        emb_content += line
    return {"emb_content" : emb_content, "tasktype" : "file"}
    

# {% embedded_image "image_name" %}
@register.simple_tag
def embedded_image(image_name):
    return ""

# {% embedded_sourcecode "file_name" %}
@register.simple_tag
def embedded_sourcecode(file_name):
    return ""
