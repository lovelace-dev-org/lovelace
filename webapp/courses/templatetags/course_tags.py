from django import template
from datetime import datetime

register = template.Library()

# {% content_meta %}
@register.inclusion_tag("courses/content-meta.html", takes_context=True)
def content_meta(context):
    return context

# {% lecture %}
@register.inclusion_tag("courses/lecture.html", takes_context=True)
def lecture(context):
    return context

# {% multiple_choice_exercise %}
@register.inclusion_tag("courses/multiple_choice_exercise.html", takes_context=True)
def multiple_choice_exercise(context):
    return context

# {% checkbox_exercise %}
@register.inclusion_tag("courses/checkbox_exercise.html", takes_context=True)
def checkbox_exercise(context):
    return context

# {% textfield_exercise %}
@register.inclusion_tag("courses/textfield_exercise.html", takes_context=True)
def textfield_exercise(context):
    return context

# {% file_upload_exercise %}
@register.inclusion_tag("courses/file_upload_exercise.html", takes_context=True)
def file_upload_exercise(context):
    return context

# {% feedbacks %}
@register.inclusion_tag("feedback/feedbacks.html", takes_context=True)
def feedbacks(context):
    return context

# {% answer_date %}
@register.filter
def answer_date(t):
    if t.date() == datetime.now().date():
        return "{:%H:%M:%S}".format(t)
    else:
        return "{:%Y-%m-%d}".format(t)
