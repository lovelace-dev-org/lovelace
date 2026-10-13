import itertools
import time
from datetime import datetime
from django.urls import reverse
from django.utils.html import mark_safe
from django import template
from lovelace import plugins as lovelace_plugins
from courses.models import Calendar, StudentGroup
from courses import markupparser
from utils.base import get_deadline_urgency
from utils.formatters import display_name

register = template.Library()


@register.filter
def full_name(user):
    return display_name(user)


@register.filter
def enrolled(user, instance):
    return instance.user_enroll_status(user)

@register.simple_tag
def render_markup(content, instance):
    context = {
        "course": instance.course,
        "instance": instance,
    }
    parser = markupparser.MarkupParser()
    return mark_safe("".join(
        block[1] for block in parser.parse(content, context=context)
    ))

@register.simple_tag(takes_context=True)
def content_page_addons(context, content_data, content_level):
    return mark_safe("\n".join(
        content_data.get_content_additions(content_data, context, content_level)
    ))


# {% base_static_extra %}
@register.inclusion_tag("courses/static-files-include.html", takes_context=True)
def base_static_extra(context):
    includes = []
    for module in lovelace_plugins["base-static"]:
        includes.extend(module.includes.get_base_static_includes(context))

    return {
        "static_includes": includes
    }

# {% content_meta %}
@register.inclusion_tag("courses/content-meta.html", takes_context=True)
def content_meta(context):
    return context

# {% answer_date %}
@register.filter
def answer_date(t):
    if t.date() == datetime.now().date():
        return mark_safe(f'<span>{t:%H:%M:%S}</span>')
    return mark_safe(f'<span title="{t:%H:%M:%S}">{t:%Y-%m-%d}</span>')


# {% event_duration %}
@register.filter
def event_duration(td):
    seconds = td.total_seconds()
    if seconds >= 3600:
        return time.strftime("%Hh %Mmin", time.gmtime(seconds))
    return time.strftime("%Mmin", time.gmtime(seconds))

@register.filter
def preview_escape(block):
    return block.replace("'", "&#x27;")

@register.inclusion_tag("courses/embed-frame.html", takes_context=True)
def embed_frame(context, content_data):
    link = context["embedded_pages"][content_data["slug"]]
    page = link.embedded_page

    content_data = page.dynamic_content(page, context, content_data)

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
        "staff_menu": content_data["staff_menu"],
        "meta": content_data["urls"],
        "revision": content_data["revision"],
        "user": context["user"],
        "enrolled": context["enrolled"],
        "course_staff": context["course_staff"],
        "course": context["course"],
        "instance": context["instance"],
        "parent": context["content"],
        "embed_link": link,
        "content": page,
        "answer_count": answer_count,
        "attempts_left": link.answer_limit and link.answer_limit - answer_count,
        "evaluation": evaluation,
        "score": quotient * content_data["max_points"],
        "max_points": content_data["max_points"],
        "editable_markups": context["editable_markups"],
    }


@register.inclusion_tag("courses/user-menu-options.html", takes_context=True)
def user_menu_extra(context):
    options = []
    for module in lovelace_plugins["user-menu"]:
        options.extend(module.includes.get_user_menu_options(context))

    return {
        "menu_options": options,
    }

@register.inclusion_tag("courses/content-menu-options.html", takes_context=True)
def content_menu_extra(context, content_data):
    options = []
    for module in lovelace_plugins["content-menu"]:
        options.extend(module.includes.get_content_menu_options(context, content_data, "staff"))

    return {
        "menu_options": options,
        "content": content_data,
        "in_list": True
    }

# The implementation above is different from the ones below because we *know* that
# content type is always Lecture in the above case whereas in the below case the
# content type is unknown and can have type specific additions to the extra menus.


@register.inclusion_tag("courses/embed-menu-options.html", takes_context=True)
def embed_student_extra(context, content_data):
    return {
        "menu_options": content_data.get_student_extra(content_data, context),
        "content": content_data,
        "in_list": False,
    }

@register.inclusion_tag("courses/embed-menu-options.html", takes_context=True)
def embed_staff_extra(context, content_data):
    return {
        "menu_options": content_data.get_staff_extra(content_data, context),
        "content": content_data,
        "in_list": True,
    }


@register.inclusion_tag("courses/embed-frame-preview.html", takes_context=False)
def embed_frame_preview(content_data):
    return {"emb": content_data}


@register.inclusion_tag("courses/calendar.html", takes_context=True)
def calendar(context, calendar_data):
    if calendar_data["calendar"] is None:
        return {
            "calendar": None
        }

    calendar = (
        Calendar.objects.filter(slug=calendar_data["calendar"])
        .prefetch_related("calendardate_set", "calendardate_set__calendarreservation_set")
        .first()
    )

    events = calendar.calendardate_set.get_queryset().order_by("start_time")
    calendar_reservations = {}

    user = context["user"]
    user_has_slot = False
    reserved_event_ids = []

    def get_event_date(event):
        return event.start_time.date()

    for event_date, cal_dates in itertools.groupby(events, get_event_date):
        calendar_reservations[event_date] = []
        for cal_date in cal_dates:
            cal_date.is_locked()
            date_reservations = []
            for reservation in cal_date.calendarreservation_set.get_queryset():
                entry = {}
                if context.get("course_staff"):
                    entry["reserver"] = display_name(reservation.user)
                    try:
                        group = StudentGroup.objects.get(
                            members=reservation.user, instance=context["instance"]
                        )
                    except StudentGroup.DoesNotExist:
                        entry["group"] = "-"
                    else:
                        memberlist = []
                        for member in group.members.get_queryset().exclude(id=reservation.user.id):
                            memberlist.append(display_name(member))
                        entry["group"] = f"({group.name})\n"
                        entry["group"] += "\n".join(memberlist)

                    if calendar.related_content:
                        entry["answers_url"] = reverse(
                            "courses:show_answers",
                            kwargs={
                                "user": reservation.user,
                                "course": context["course"],
                                "instance": context["instance"],
                                "exercise": calendar.related_content,
                            },
                        )
                    else:
                        entry["answers_url"] = reverse(
                            "teacher:student_completion",
                            kwargs={
                                "user": reservation.user,
                                "course": context["course"],
                                "instance": context["instance"],
                            },
                        )
                    entry["message_url"] = reverse(
                        "courses:send_message",
                        kwargs={
                            "user": reservation.user,
                            "course": context["course"],
                            "instance": context["instance"],
                        },
                    )

                date_reservations.append(entry)
                if reservation.user == user:
                    user_has_slot = True
                    reserved_event_ids.append(cal_date.id)

            calendar_reservations[event_date].append((cal_date, date_reservations))


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
    calendar = (
        Calendar.objects.filter(name=calendar_data["calendar"])
        .prefetch_related("calendardate_set")
        .first()
    )

    cal_dates = calendar.calendardate_set.get_queryset().order_by("start_time")
    calendar_reservations = []
    for cal_date in cal_dates:
        date_reservations = []
        calendar_reservations.append((cal_date, date_reservations))
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
        "submit_url": reverse(
            "courses:set_supervisor",
            kwargs={
                "course": context["course"],
                "instance": context["instance"],
                "group": group,
            },
        ),
    }

@register.inclusion_tag("courses/widgets/enroll_widget.html", takes_context=True)
def enroll_widget(context, course, instance, enroll_status):
    return {
        "course": course,
        "instance": instance,
        "user_authenticated": context["user"].is_authenticated,
        "enroll_status": enroll_status,
    }

@register.inclusion_tag("courses/widgets/progress_widget.html", takes_context=True)
def progress_widget(context, node_item):
    page_score = 0
    page_correct = 0
    for group, tasks in node_item["embeds"].items():
        if group == "":
            for task_id, point_value in tasks:
                point_value = point_value * node_item["weight"]
                if task_id in context["student_results"]:
                    quotient = context["student_results"][task_id]["points"]
                    page_correct += bool(quotient)
                    page_score += point_value * quotient
        else:
            best_result = 0
            for task_id, point_value in tasks:
                point_value = point_value * node_item["weight"]
                if task_id in context["student_results"]:
                    best_result = max(
                        context["student_results"][task_id]["points"] * point_value, best_result
                    )
            page_correct += bool(best_result)
            page_score += best_result


    deadline = context["exemptions"].get(node_item["node_id"], node_item["deadline"])
    urgency = get_deadline_urgency(deadline, context["time_now"])
    if deadline:
        dl_string = deadline.strftime("%Y-%m-%d, %H:%M")
    else:
        dl_string = ""

    return {
        "correct_embedded": page_correct,
        "embedded_count": node_item["embedded_count"],
        "page_max": f"{node_item['page_score'] * node_item['weight']:.2f}",
        "page_score": f"{page_score:.2f}",
        "deadline": dl_string,
        "dl_urgency": urgency
    }






