import datetime
import os

from django.conf import settings
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

from courses.forms import process_delete_confirm_form
from courses.models import User


from utils.access import ensure_enrolled_or_staff, determine_access, ensure_staff, ensure_responsible
from utils.archive import find_latest_version
from utils.content import get_embedded_parent
from utils.files import generate_download_response, get_file_contents_b64

from multiexam.models import (
    ExamQuestionPool,
    MultipleQuestionExam,
    MultipleQuestionExamAttempt,
    UserMultipleQuestionExamAnswer
)
from multiexam.forms import ExamAttemptForm, ExamAttemptDeleteForm, ExamAttemptSettingsForm
from multiexam.utils import generate_attempt_questions, process_questions

@ensure_enrolled_or_staff
def get_exam_attempt(request, course, instance, content):
    """
    Gets an attempt for an exam. Tries to find an open attempt, and gives an error if one is not
    found. In case multiple attempts are open for some eason, picks the first one. Also checks if
    the user already has existing answers for the attempt, and loads the latest answer if at least
    one exists.
    """

    now = datetime.datetime.now()
    open_attempts = MultipleQuestionExamAttempt.objects.filter(
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

    answer = UserMultipleQuestionExamAnswer.objects.filter(
        attempt=attempt,
        user=request.user,
    ).order_by("-answer_date").first()

    if answer is None:
        answered_choices = {}
    else:
        answered_choices = answer.answers

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
    """
    Management view for exam attempts.
    """

    attempts = MultipleQuestionExamAttempt.objects.filter(
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
    """
    View for opening a new attempt. Depending on the HTTP method used either displays the form,
    or saves a filled form. Generation of questions for the attempt is also done at this point.
    """

    if request.method == "POST":
        form = ExamAttemptForm(
            request.POST,
            students=instance.enrolled_users.get_queryset(),
            available_questions=content.examquestionpool.question_count()
        )
        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        if form.cleaned_data.get("user_id", None):
            user = User.objects.get(id=form.cleaned_data["user_id"])
        else:
            user = None
        attempt = form.save(commit=False)
        attempt.instance = instance
        attempt.exam = content
        attempt.questions = generate_attempt_questions(
            content, instance, form.cleaned_data["question_count"], user
        )
        attempt.revision = find_latest_version(content).revision_id
        attempt.user = user
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
    """
    View for getting a preview for an exam attempt.
    """

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
    """
    A view for changing attempt settings.
    """

    if request.method == "POST":
        form = ExamAttemptSettingsForm(request.POST, instance=attempt)
        if not form.is_valid():
            errors = form.errors_as_json()
            return JsonResponse({"errors": errors}, status=400)

        attempt = form.save(commit=False)
        if form.cleaned_data["refresh"]:
            attempt.revision = find_latest_version(attempt.exam).revision_id
        attempt.save()

        return JsonResponse({"status": "ok"})

    form = ExamAttemptSettingsForm(instance=attempt)
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"attempt-settings-form",
        "html_class": "management-form",
    }
    return HttpResponse(form_t.render(form_c, request))

@ensure_responsible
def delete_attempt(request, course, instance, attempt):
    """
    View for deleting an attempt.
    """

    def success(form):
        attempt.delete()

    extra = {
        "disclaimer": _(
            "If an attempt is deleted, all existing answers will be lost. "
            "You can close the attempt by changing its end date if you want to "
            "retain existing answers while making the exam attempt unavailable."
        ),
    }
    return process_delete_confirm_form(request, success, extra)

def download_question_pool(request, exercise_id, field_name, filename):
    try:
        exercise_object = MultipleQuestionExam.objects.get(id=exercise_id)
    except MultipleQuestionExam.DoesNotExist as e:
        return HttpResponseNotFound(_("This exercise does't exist"))

    if not determine_access(request.user, exercise_object):
        return HttpResponseForbidden(
            _(
                "Only course main responsible teachers are allowed "
                "to download files through this interface."
            )
        )

    fileobjects = ExamQuestionPool.objects.filter(exercise=exercise_object)
    try:
        for fileobject in fileobjects:
            if filename == os.path.basename(getattr(fileobject, field_name).name):
                fs_path = os.path.join(
                    settings.PRIVATE_STORAGE_FS_PATH, getattr(fileobject, field_name).name
                )
                break

            # Archived file was requested
            version = find_version_with_filename(fileobject, field_name, filename)
            if version:
                filename = version.field_dict[field_name].name
                fs_path = os.path.join(settings.PRIVATE_STORAGE_FS_PATH, filename)
                break
        else:
            return HttpResponseNotFound(_("Requested file does not exist."))
    except AttributeError as e:
        return HttpResponseNotFound(_("Requested file does not exist."))

    return generate_download_response(fs_path)
