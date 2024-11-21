import datetime
from django.conf import settings
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.template import loader
from django.utils import translation
from courses.forms import SystemMessageForm
from utils.access import ensure_admin
from utils.notify import create_notifications, get_notifications, delete_notification

@ensure_admin
def manage_system_messages(request):
    if request.method == "POST":
        form = SystemMessageForm(request.POST)

        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        create_notifications(
            form.cleaned_data,
            form.cleaned_data["expires"],
        )

    else:
        form = SystemMessageForm()

    notifications = get_notifications(
        "system",
        datetime.datetime.fromtimestamp(0).isoformat(),
        translation.get_language(),
        return_keys=True,
    )

    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "system-message-form",
    }

    t = loader.get_template("courses/system-messages.html")
    c = {
        "form": form_t.render(form_c, request),
        "system_messages": notifications,
    }

    return HttpResponse(t.render(c, request))

@ensure_admin
def remove_system_message(request, msg_key):
    __, timestamp, __ = msg_key.split("_")
    delete_notification("system", timestamp)
    return JsonResponse({"status": "ok"})

