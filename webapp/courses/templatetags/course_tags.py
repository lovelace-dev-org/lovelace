import time
from django.urls import reverse
from django import template
from datetime import datetime
from courses.models import Calendar, StudentGroup
from utils.formatters import display_name

register = template.Library()

@register.filter
def full_name(user):
    return display_name(user)

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
    if seconds >= 3600:
        return time.strftime("%Hh %Mmin", time.gmtime(seconds))
    else:
        return time.strftime("%Mmin", time.gmtime(seconds))
    
@register.inclusion_tag("courses/embed-frame.html", takes_context=True)
def embed_frame(context, content_data):
    page = context["embedded_pages"][content_data["slug"]]
    if context["user"].is_active:
        answer_count = page.get_user_answers(page, context["user"], context["instance"]).count()
        evaluation, quotient = page.get_user_evaluation(context["user"], context["instance"])
    else:
        answer_count = 0
        evaluation = None
        quotient = 0
    
    return {
        "emb": content_data,
        "embedded": True,
        "meta": content_data["urls"],
        "revision": content_data["revision"],
        "user": context["user"],
        "enrolled": context["enrolled"],
        "course_staff": context["course_staff"],
        "course": context["course"],
        "instance": context["instance"],
        "content": page,
        "answer_count": answer_count,
        "evaluation": evaluation,
        "score": quotient * content_data["max_points"],
        "max_points": content_data["max_points"]
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
    calendar_reservations = []
    
    user = context["user"]
    user_has_slot = False
    reserved_event_ids = []
    
    for cal_date in cal_dates:        
        date_reservations = []
        for reservation in cal_date.calendarreservation_set.get_queryset():
            entry = {}
            if context.get("course_staff"):
                entry["reserver"] = display_name(reservation.user)
                try:
                    group = StudentGroup.objects.get(members=reservation.user)
                except StudentGroup.DoesNotExist:
                    entry["group"] = "-"
                else:
                    memberlist = []
                    for member in group.members.get_queryset().exclude(id=reservation.user.id):
                        memberlist.append(display_name(member))
                    entry["group"] = "({})\n".format(group.name)
                    entry["group"] += "\n".join(memberlist)
                    
                if calendar.related_content:
                    entry["answers_url"] = reverse("courses:show_answers", kwargs={
                        "user": reservation.user,
                        "course": context["course"],
                        "instance": context["instance"],
                        "exercise": calendar.related_content
                    })
                else:
                    entry["answers_url"] = reverse("teacher:student_completion", kwargs={
                        "user": reservation.user,
                        "course": context["course"],
                        "instance": context["instance"],
                    })
                entry["message_url"] = reverse("courses:send_message", kwargs={
                        "user": reservation.user,
                        "course": context["course"],
                        "instance": context["instance"],
                })
            
            date_reservations.append(entry)            
            if reservation.user == user:
                user_has_slot = True
                reserved_event_ids.append(cal_date.id)
        
        calendar_reservations.append((
            cal_date,
            date_reservations
        ))

    can_reserve = True
    if user_has_slot and not calendar.allow_multiple:
        can_reserve = False
                
    return {
        "course": context["course"],
        "instance": context["instance"],
        "user": user,
        "can_reserve": can_reserve,
        "calendar": calendar,
        "course_staff": context["course_staff"],
        "cal_reservations": calendar_reservations,
        "reserved_event_ids": reserved_event_ids,
    }
    
@register.inclusion_tag("courses/calendar-preview.html", takes_context=False)
def calendar_preview(calendar_data):
    calendar = Calendar.objects.filter(
        name=calendar_data["calendar"]
    ).prefetch_related(
        "calendardate_set"
    ).first()
    
    cal_dates = calendar.calendardate_set.get_queryset().order_by("start_time")
    calendar_reservations = []
    for cal_date in cal_dates:        
        date_reservations = []
        calendar_reservations.append((
            cal_date,
            date_reservations
        ))
    return {
        "calendar": calendar,
        "cal_reservations": calendar_reservations,
    }
    

@register.inclusion_tag("courses/widgets/group_supervisor_select.html", takes_context=True)
def supervisor_select(context, group):
    return {
        "staff": context["staff"],
        "selected": group.supervisor,
        "csrf_token": context["csrf_token"],
        "submit_url": reverse("courses:set_supervisor", kwargs={
            "course": context["course"],
            "instance": context["instance"],
            "group": group,
        })
    }
