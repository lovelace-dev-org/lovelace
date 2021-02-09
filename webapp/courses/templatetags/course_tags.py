import time
from django import template
from datetime import datetime
from courses.models import Calendar

register = template.Library()

@register.filter
def enrolled(user, instance):
    return instance.user_enroll_status(user)

# {% content_meta %}
@register.inclusion_tag("courses/content-meta.html", takes_context=True)
def content_meta(context):
    return context

# {% lecture %}
@register.inclusion_tag("courses/lecture.html", takes_context=True)
def lecture(context):
    return context

# {% multiple_choice_exercise %}
@register.inclusion_tag("courses/multiple-choice-exercise.html", takes_context=True)
def multiple_choice_exercise(context):
    return context

# {% checkbox_exercise %}
@register.inclusion_tag("courses/checkbox-exercise.html", takes_context=True)
def checkbox_exercise(context):
    return context

# {% textfield_exercise %}
@register.inclusion_tag("courses/textfield-exercise.html", takes_context=True)
def textfield_exercise(context):
    return context

# {% file_upload_exercise %}
@register.inclusion_tag("courses/file-upload-exercise.html", takes_context=True)
def file_upload_exercise(context):
    return context

# {% feedbacks %}
@register.inclusion_tag("feedback/feedbacks.html", takes_context=True)
def feedbacks(context):
    return context

@register.inclusion_tag("faq/faq.html", takes_context=True)
def faq(context):
    return context
    
# {% answer_date %}
@register.filter
def answer_date(t):
    if t.date() == datetime.now().date():
        return "{:%H:%M:%S}".format(t)
    else:
        return "{:%Y-%m-%d}".format(t)

# {% event_duration %}
@register.filter
def event_duration(td):
    seconds = td.total_seconds()
    if seconds > 3600:
        return time.strftime("%Hh %Mmin", time.gmtime(seconds))
    else:
        return time.strftime("%Mmin", time.gmtime(seconds))
    
@register.inclusion_tag("courses/embed-frame.html", takes_context=True)
def embed_frame(context, content_data):
    page = context["embedded_pages"][content_data["slug"]]
    if context["user"].is_active:
        answer_count = page.get_user_answers(page, context["user"], context["instance"]).count()
        evaluation = page.get_user_evaluation(context["user"], context["instance"])
    else:
        answer_count = 0
        evaluation = None
    
    return {
        "emb": content_data,
        "embedded": True,
        "meta": content_data["urls"],
        "user": context["user"],
        "enrolled": context["enrolled"],
        "course_staff": context["course_staff"],
        "course": context["course"],
        "instance": context["instance"],
        "content": page,
        "answer_count": answer_count,
        "evaluation": evaluation
    }

@register.inclusion_tag("courses/embed-frame-preview.html", takes_context=False)
def embed_frame_preview(content_data):
    return {
        "emb": content_data
    }
    
@register.inclusion_tag("courses/calendar.html", takes_context=True)
def calendar(context, calendar_data):
    calendar = Calendar.objects.filter(
        name=calendar_data["calendar"]
    ).prefetch_related(
        "calendardate_set", "calendardate_set__calendarreservation_set"
    ).first()
        
    cal_dates = calendar.calendardate_set.get_queryset().order_by("start_time")
    calendar_reservations = [
        (
            cal_date, 
            [cal_date.calendarreservation_set.get_queryset(), False]
        )
        for cal_date in cal_dates
    ]
    user = context["user"]
    user_has_slot = False
    reserved_event_ids = []

    if user.is_authenticated:
        for cal_date, cal_reservations in calendar_reservations:
            try:
                found = cal_reservations[0].get(user=user)
            except:
                continue
            cal_reservations[1] = True
            user_has_slot = True
            reserved_event_ids.append(found.calendar_date.id)
    
    if user_has_slot and not calendar.allow_multiple:
        for cal_date, cal_reservations in calendar_reservations:
            cal_reservations[1] = True
    
    return {
        "user": user,
        "cal_id": calendar.id,
        "cal_reservations": calendar_reservations,
        "reserved_event_ids": reserved_event_ids,
    }
