import hashlib
from datetime import datetime
from django import template

ENCODING = "utf-8"

register = template.Library()

# {% feedback_textfield %}
@register.inclusion_tag("feedback/textfield_feedback_question.html")
def feedback_textfield(question, user, content):
    return {"question" : question.question,
            "answered" : question.user_answered(user, content) if user.is_authenticated() else None,
            "content_slug" : content.slug, 
            "feedback_slug" : question.slug}

# {% feedback_thumb %}
@register.inclusion_tag("feedback/thumb_feedback_question.html")
def feedback_thumb(question, user, content):
    if user.is_authenticated() and question.user_answered(user, content):
        user_answer = question.get_latest_answer(user, content).thumb_up 
    else:
        user_answer = None

    return {"question" : question.question,
            "user_answer" : user_answer, 
            "content_slug" : content.slug, 
            "feedback_slug" : question.slug}

# {% feedback_star %}
@register.inclusion_tag("feedback/star_feedback_question.html")
def feedback_star(question, user, content):
    if user.is_authenticated() and question.user_answered(user, content):
        user_answer = question.get_latest_answer(user, content).rating
    else:
        user_answer = None

    return {"question" : question.question,
            "user_answer" : user_answer,
            "content_slug" : content.slug, 
            "feedback_slug" : question.slug,
            "radiobutton_id" : hashlib.md5(bytearray(question.slug + content.slug, "utf-8")).hexdigest()}

# {% sortable_table_header %}
@register.inclusion_tag("feedback/sortable_table_header.html")
def sortable_table_header(slug, header, column):
    return {
        "slug": slug,
        "header": header,
        "column": column,
    }

# {% answer_date %}
@register.filter
def answer_date(t):
    if t.date() == datetime.now().date():
        return "{:%H:%M:%S}".format(t)
    else:
        return "{:%Y-%m-%d}".format(t)

