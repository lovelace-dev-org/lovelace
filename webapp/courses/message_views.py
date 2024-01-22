from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseForbidden,
)
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _
from courses.models import SavedMessage
from courses.forms import MessageForm
from utils.access import ensure_staff, ensure_responsible
from utils.formatters import display_name
from utils.notify import send_email, send_bcc_email


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
