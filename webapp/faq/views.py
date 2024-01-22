import reversion
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    JsonResponse,
)
from django.utils.translation import gettext as _
from faq.models import FaqQuestion, FaqToInstanceLink
from faq.forms import FaqQuestionForm
from faq.utils import regenerate_cache, render_panel
from utils.access import ensure_staff


def get_faq_panel(request, course, instance, exercise):
    preopen_hooks = request.GET.getlist("preopen")
    return HttpResponse(render_panel(request, course, instance, exercise, preopen_hooks))


@ensure_staff
def save_question(request, course, instance, exercise):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    if instance.frozen:
        return HttpResponseForbidden(_("Cannot edit FAQ for frozen instance"))

    try:
        question = FaqQuestion.objects.filter(hook=request.POST["hook"]).first()
    except KeyError:
        return HttpResponseBadRequest()

    if request.POST["action"] == "create":
        form = FaqQuestionForm(request.POST)
    else:
        form = FaqQuestionForm(request.POST, instance=question)

    if not form.is_valid():
        errors = form.errors.as_json()
        return JsonResponse({"errors": errors}, status=400)

    with reversion.create_revision():
        saved_question = form.save(commit=True)
        reversion.set_user(request.user)
    if question is None:
        link = FaqToInstanceLink(
            question=saved_question,
            instance=instance,
            exercise=exercise,
        )
        link.save()
    regenerate_cache(instance, exercise)
    content = render_panel(request, course, instance, exercise)
    return JsonResponse({"content": content})


@ensure_staff
def get_editable_question(request, course, instance, exercise, hook):
    try:
        question = FaqQuestion.objects.get(hook=hook)
    except FaqQuestion.DoesNotExist:
        return HttpResponseNotFound()

    return JsonResponse(
        {"question": question.question, "answer": question.answer, "hook": question.hook}
    )


@ensure_staff
def link_question(request, course, instance, exercise):
    try:
        question = FaqQuestion.objects.get(
            hook=request.POST["question_select"],
        )
    except FaqQuestion.DoesNotExist:
        return HttpResponseNotFound()

    link = FaqToInstanceLink(
        exercise=exercise,
        instance=instance,
        question=question,
    )
    link.save()
    regenerate_cache(instance, exercise)
    content = render_panel(request, course, instance, exercise)
    return JsonResponse({"content": content})


@ensure_staff
def unlink_question(request, course, instance, exercise, hook):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    try:
        FaqToInstanceLink.objects.get(
            instance=instance, exercise=exercise, question__hook=hook
        ).delete()
    except FaqToInstanceLink.DoesNotExist:
        return HttpResponseNotFound(_("The question is not linked"))

    regenerate_cache(instance, exercise)
    return HttpResponse(status=204)
