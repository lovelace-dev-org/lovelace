import datetime

from django.db.models import Q
from django.http import (
    HttpResponse,
    JsonResponse,
    HttpResponseNotFound,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseBadRequest,
)
from django.shortcuts import render
from django.template import loader
from django.utils.translation import gettext as _

from utils.access import ensure_enrolled_or_staff, determine_access, ensure_staff, ensure_responsible
from utils.archive import find_latest_version
from utils.content import get_embedded_parent

from multiexam.models import MultipleChoiceExamAttempt, UserMultipleChoiceExamAnswer
from multiexam.forms import ExamAttemptForm, ExamAttemptDeleteForm, ExamAttemptSettingsForm
from multiexam.utils import generate_attempt_questions, process_questions

# Create your views here.

@ensure_enrolled_or_staff
def get_exam_attempt(request, course, instance, content):
    now = datetime.datetime.now()
    open_attempts = MultipleChoiceExamAttempt.objects.filter(
        Q(user=None) | Q(user=request.user),
        exam=content,
        instance=instance,
        open_from__lt=now,
        open_to__gt=now,
    )
    if not open_attempts:
        return JsonResponse({
            "error": _("You don't have an open attempt for this exam.")
        })

    attempt = open_attempts.first()
    script = attempt.load_exam_script()

    answer = UserMultipleChoiceExamAnswer.objects.filter(
        attempt=attempt,
        user=request.user,
    ).order_by("-answer_date").first()

    if answer is None:
        answered_choices = {}
    else:
        answered_choices = answer.answers

    print(answered_choices)

    question_states = process_questions(request, script, answered_choices)

    c = {
        "attempt_script": script,
        "attempt_id": attempt.id,
        "n_answered": len(answered_choices),
        "n_total": len(script),
        "question_states": question_states
    }
    t = loader.get_template("multiexam/exam-form.html")
    return JsonResponse({
        "rendered_form": t.render(c, request),
    })

@ensure_responsible
def manage_attempts(request, course, instance, content):
    attempts = MultipleChoiceExamAttempt.objects.filter(
        exam=content,
        instance=instance,
    )
    parent, single_linked = get_embedded_parent(content, instance)
    t = loader.get_template("multiexam/manage-attempts.html")
    c = {
        "course": course,
        "instance": instance,
        "course_staff": True,
        "content": content,
        "parent": parent,
        "single_linked": single_linked,
        "attempts": attempts,
    }
    return HttpResponse(t.render(c, request))

@ensure_responsible
def open_new_attempt(request, course, instance, content):
    if request.method == "POST":
        form = ExamAttemptForm(
            request.POST,
            students=instance.enrolled_users.get_queryset(),
            available_questions=content.examquestionpool.question_count()
        )
        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        attempt = form.save(commit=False)
        attempt.instance = instance
        attempt.exam = content
        attempt.questions = generate_attempt_questions(
            content, instance, form.cleaned_data["question_count"], form.cleaned_data["user"]
        )
        attempt.revision = find_latest_version(content).revision_id
        attempt.save()
        return JsonResponse({"status": "ok"})

    form = ExamAttemptForm(
        students=instance.enrolled_users.get_queryset(),
        available_questions=content.examquestionpool.question_count()
    )
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"open-attempt-form",
        "html_class": "exam-management-form",
    }
    return HttpResponse(form_t.render(form_c, request))


@ensure_responsible
def preview_attempt(request, course, instance, attempt):
    script = attempt.load_exam_script()
    process_questions(request, script, {})
    c = {
        "attempt_script": script,
        "attempt_id": attempt.id,
        "answers": {},
        "preview": True,
    }
    t = loader.get_template("multiexam/exam-form.html")
    return HttpResponse(t.render(c, request))


@ensure_responsible
def attempt_settings(request, course, instance, attempt):
    if request.method == "POST":
        form = ExamAttemptDeleteForm(request.POST, instance=attempt)
        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        attempt = form.save(commit=False)
        if form.cleaned_data["refresh"]:
            attempt.revision = find_latest_version(attempt.exam).revision_id

        return JsonResponse({"status": "ok"})

    form = ExamAttemptSettingsForm(instance=attempt)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"attempt-settings-form",
        "html_class": "exam-management-form",
    }
    return HttpResponse(form_t.render(form_c, request))

@ensure_responsible
def delete_attempt(request, course, instance, attempt):
    if request.method == "POST":
        form = ExamAttemptDeleteForm(request.POST)
        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        attempt.delete()
        return JsonResponse({"status": "ok"})

    form = ExamAttemptDeleteForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"delete-attempt-form",
        "html_class": "exam-management-form",
        "disclaimer": _(
            "If an attempt is deleted, all existing answers will be lost. "
            "You can close the attempt by changing its end date if you want to "
            "retain existing answers while making the exam attempt unavailable."
        ),
        "submit_label": _("Execute"),
    }
    return HttpResponse(form_t.render(form_c, request))











