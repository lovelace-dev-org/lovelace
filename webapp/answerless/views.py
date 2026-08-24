from decimal import Decimal
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.shortcuts import render
from django.template import loader
from django.utils.translation import gettext_lazy as _

from reversion.models import Version

import courses.models as cm

from .forms import StudentEntryForm

# Create your views here.

def add_student_entry(request, course, instance, parent, content):

    enrolled_students = instance.enrolled_users.get_queryset()

    if request.method == "POST":
        form = StudentEntryForm(request.POST, students=enrolled_students)
        if not form.is_valid():
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        embed_link = cm.EmbeddedLink.objects.get(
            embedded_page=content, instance=instance, parent=parent
        )
        if embed_link.revision is None:
            latest = Version.objects.get_for_object(content).latest("revision__date_created")
            answered_revision = latest.revision_id
        else:
            answered_revision = embed_link.revision

        user = form.cleaned_data["user"]
        answer_object = content.save_answer(
            content,
            user,
            request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR"),
            request.POST,
            None,
            instance,
            answered_revision
        )
        evaluation = content.check_answer(
            content, embed_link, user, request.POST, None, answer_object
        )
        evaluation["points"] = Decimal(evaluation.get("quotient", 0)) * embed_link.default_points
        if embed_link.manually_evaluated:
            evaluation["manual"] = True
            evaluation["evaluation"] = False
        else:
            evaluation["manual"] = False

        content.save_evaluation(embed_link, user, evaluation, answer_object)
        return JsonResponse({"status": "ok"})

    form = StudentEntryForm(students=enrolled_students)
    t = loader.get_template("courses/base-edit-form.html")
    c = {
        "html_id": f"{content.slug}-answerless-entry-form",
        "form_object": form,
        "submit_url": request.path,
        "html_class": "edit-form-widget",
        "submit_override": "editing.submit_form"
    }
    return HttpResponse(t.render(c, request))

