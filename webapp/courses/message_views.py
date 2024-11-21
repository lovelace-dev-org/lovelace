from collections import defaultdict
import datetime
from django.conf import settings
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseForbidden,
    HttpResponseNotFound,
)
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils import translation
from courses.models import SavedMessage, CourseMessage, CourseEnrollment
from courses.forms import MessageForm, CourseMessageForm
from utils.access import ensure_staff, ensure_responsible, ensure_enrolled_or_staff
from utils.formatters import display_name
from utils.notify import (
    send_email,
    send_bcc_email,
    create_notifications,
    delete_notification,
    get_notifications,
)


# Email Messages
# |
# v

def process_message_form(request, course, instance, recipients, form_label="", use_bcc=False):
    saved_msgs = SavedMessage.objects.filter(course=course)
    load_url = reverse(
        "courses:load_message", kwargs={"course": course, "instance": instance, "msgid": 0}
    )

    if request.method == "POST":
        form = MessageForm(request.POST, saved=saved_msgs, load_url=load_url)
        if not form.is_valid():
            errors = form.errors.as_json()
            return JsonResponse({"errors": errors}, status=400)

        loaded_message = saved_msgs.filter(id=form.cleaned_data["saved_msgs"]).first()
        original_handle = loaded_message and loaded_message.handle
        form = MessageForm(
            request.POST, saved=saved_msgs, load_url=load_url, instance=loaded_message
        )

        message = form.save(commit=False)
        if form.cleaned_data["confirm_save"] and message.handle:
            message.course = course
            if original_handle == message.handle:
                message.save()
            else:
                message.pk = None
                message.save()

        if use_bcc:
            send_bcc_email(
                instance,
                recipients,
                request.user,
                message.render_title(),
                message.render_content(),
            )
        else:
            send_email(recipients, request.user, message.render_title(), message.render_content())
        return JsonResponse({"status": "ok"})

    form_object = MessageForm(load_url=load_url, saved=saved_msgs)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form_object,
        "submit_url": request.path,
        "html_class": "side-panel-form",
        "disclaimer": form_label,
        "submit_label": _("Send"),
    }
    t = loader.get_template("courses/direct-message-panel.html")
    c = {"form": form_t.render(form_c, request)}
    return HttpResponse(t.render(c, request))


@ensure_staff
def direct_message(request, course, instance, user):
    enrolled_students = instance.enrolled_users.get_queryset()
    if enrolled_students.filter(id=user.id).exists():
        return process_message_form(
            request,
            course,
            instance,
            recipients=[user],
            form_label=_("Send a message to {user}").format(user=display_name(user)),
        )
    return HttpResponseForbidden(_("User is not enrolled to this course instance"))


@ensure_responsible
def mass_email(request, course, instance):
    recipients = instance.enrolled_users.get_queryset().filter(
        courseenrollment__enrollment_state="ACCEPTED"
    )
    return process_message_form(
        request,
        course,
        instance,
        recipients=recipients,
        form_label=_("Send message to all enrolled users"),
        use_bcc=True,
    )


@ensure_staff
def load_message(request, course, instance, msgid):
    try:
        message = SavedMessage.objects.get(course=course, id=msgid)
    except SavedMessage.DoesNotExist:
        message = SavedMessage()

    return JsonResponse(message.serialize_translated())

# ^
# |
# Email Messages
# Lovelace Messages
# |
# v

@ensure_responsible
def course_messages(request, course, instance):
    if request.method == "POST":
        form = CourseMessageForm(request.POST)

        if not form.is_valid():
            errors = form.errors_as_json()
        else:
            message = form.save(commit=False)
            message.instance = instance
            message.save()

            session_lang = translation.get_language()
            notifications = {}
            for lang, __ in settings.LANGUAGES:
                if getattr(message, f"title_{lang}"):
                    translation.activate(lang)
                    notifications[f"content_{lang}"] = _("New message in {course}: {title}").format(
                        course=course.name,
                        title=message.title,
                    )
            translation.activate(session_lang)

            create_notifications(
                notifications,
                form.cleaned_data["expires"],
                instance=instance.slug,
                timestamp=message.created.isoformat(),
            )

            users = (
                instance.enrolled_users.get_queryset()
                .filter(courseenrollment__enrollment_state="ACCEPTED")
            )

            for user in users:
                user.userprofile.unread_messages += 1
                user.userprofile.save()

    else:
        form = CourseMessageForm()

    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "system-message-form",
    }

    messages = CourseMessage.objects.filter(instance=instance)

    t = loader.get_template("courses/course-messages.html")
    c = {
        "form": form_t.render(form_c, request),
        "course": course,
        "instance": instance,
        "course_msgs": messages,
    }

    return HttpResponse(t.render(c, request))

@ensure_responsible
def remove_course_message(request, course, instance, msgid):
    try:
        message = CourseMessage.objects.get(id=msgid)
    except CourseMessage.DoesNotExist:
        return HttpResponseNotFound

    delete_notification(instance, message.created.isoformat())
    message.delete()
    return JsonResponse({"status": "ok"})


def view_messages(request):
    by_instance = defaultdict(list)
    for enrollment in CourseEnrollment.get_user_enrollments(request.user):
        instance_messages = (
            CourseMessage.objects.filter(instance=enrollment.instance)
            .order_by("-created")
        )
        by_instance[enrollment.instance.name].extend(instance_messages)

    system_messages = get_notifications(
        "system",
        datetime.datetime.fromtimestamp(0).isoformat(),
        translation.get_language(),
    )

    request.user.userprofile.unread_messages = 0
    request.user.userprofile.save()

    t = loader.get_template("courses/messages.html")
    c = {
        "by_instance": dict(by_instance),
        "system_messages": system_messages,
    }
    return HttpResponse(t.render(c, request))





