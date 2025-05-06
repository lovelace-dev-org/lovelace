import hashlib
from datetime import datetime
from django import template

ENCODING = "utf-8"

register = template.Library()


# {% feedback_textfield %}
@register.inclusion_tag("feedback/textfield-feedback-question.html")
def feedback_textfield(question, user, content, instance):
    return {
        "question": question,
        "answered": question.user_answered(user, instance, content)
        if user.is_authenticated
        else None,
        "content": content,
        "instance": instance,
    }


# {% feedback_thumb %}
@register.inclusion_tag("feedback/thumb-feedback-question.html")
def feedback_thumb(question, user, content, instance):
    if user.is_authenticated and question.user_answered(user, instance, content):
        user_answer = question.get_latest_answer(user, instance, content).thumb_up
    else:
        user_answer = None

    return {
        "question": question,
        "user_answer": user_answer,
        "content": content,
        "instance": instance,
    }


# {% feedback_star %}
@register.inclusion_tag("feedback/star-feedback-question.html")
def feedback_star(question, user, content, instance):
    if user.is_authenticated and question.user_answered(user, instance, content):
        user_answer = question.get_latest_answer(user, instance, content).rating
    else:
        user_answer = None

    return {
        "question": question,
        "user_answer": user_answer,
        "content": content,
        "instance": instance,
        "radiobutton_id": hashlib.md5(bytearray(question.slug + content.slug, "utf-8")).hexdigest(),
    }


# {% feedback_multiple_choice %}
@register.inclusion_tag("feedback/multiple-choice-feedback-question.html")
def feedback_multiple_choice(question, user, content, instance):
    if user.is_authenticated and question.user_answered(user, instance, content):
        user_answer = question.get_latest_answer(user, instance, content).chosen_answer
    else:
        user_answer = None

    return {
        "question": question,
        "user_answer": user_answer,
        "content": content,
        "instance": instance,
        "choices": question.get_choices(),
        "radiobutton_id": hashlib.md5(bytearray(question.slug + content.slug, "utf-8")).hexdigest(),
    }


# {% sortable_table_header %}
@register.inclusion_tag("feedback/sortable-table-header.html")
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
