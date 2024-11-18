from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.template import loader
from courses.forms import SystemMessageForm
from utils.access import ensure_admin

@ensure_admin
def manage_system_messages(request):
    if request.method == "POST":
        form = SystemMessageForm(request.POST)

        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        return JsonResponse({"status": "ok"})

    form = SystemMessageForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": "system-message-form",
    }

    t = loader.get_template("courses/system-messages.html")
    c = {
        "form": form_t.render(form_c, request),
    }

    return HttpResponse(t.render(c, request))

