import datetime
import os

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
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

from courses.models import User

from utils.access import ensure_enrolled_or_staff, determine_access, ensure_staff, ensure_responsible
from utils.archive import get_single_archived, find_latest_version, find_version_with_filename
from utils.content import get_embedded_parent, download_exercise_backend
from utils.files import generate_download_response, get_file_contents_b64
from utils.management import process_delete_confirm_form, process_modelform

from multiexam.models import (
    load_pool_file,
    ExamQuestionPool,
    MultipleQuestionExam,
    MultipleQuestionExamAttempt,
    UserMultipleQuestionExamAnswer
)
from multiexam.forms import (
    ExamAttemptForm,
    ExamAttemptDeleteForm,
    ExamAttemptSettingsForm,
    ExamAttemptRefreshForm,
    ExamAttemptKeyForm,
    QuestionPoolForm,
)
from multiexam.utils import compare_exams, generate_attempt_questions, process_questions

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
    if attempt.key:
        if request.method == "POST":
            form = ExamAttemptKeyForm(request.POST, attempt=attempt)
            if not form.is_valid():
                errors = form.errors.get_json_data()
                return JsonResponse({"errors": errors}, status=400)
        else:
            form = ExamAttemptKeyForm(attempt=attempt)
            form_t = loader.get_template("courses/base-edit-form.html")
            form_c = {
                "form_object": form,
                "submit_url": request.path,
                "html_id": f"attempt-key-form",
                "html_class": "exam-key-form",
                "submit_override": "exam.submit_key",
                "submit_label": _("Send"),
            }
            return HttpResponse(form_t.render(form_c, request))

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

# ^
# |
# STUDENT VIEWS
# ATTEMPT MANAGEMENT
# |
# v

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
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        if form.cleaned_data.get("user_id", None):
            users = [User.objects.get(id=form.cleaned_data["user_id"])]
        else:
            if form.cleaned_data.get("individual_exams"):
                users = (
                    instance.enrolled_users.get_queryset()
                    .filter(courseenrollment__enrollment_state="ACCEPTED")
                )
            else:
                users = [None]
        attempt = form.save(commit=False)
        attempt.instance = instance
        attempt.exam = content
        attempt.revision = find_latest_version(content).revision_id
        attempt.set_key(form.cleaned_data["key"])
        for user in users:
            attempt.pk = None
            attempt.questions = generate_attempt_questions(
                content, instance, form.cleaned_data["question_count"], user
            )
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
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        attempt = form.save(commit=False)
        if form.cleaned_data["refresh"]:
            pools = {
                "None": load_pool_file(attempt.exam.examquestionpool.fileinfo),
                "Attempt": load_pool_file(
                    get_single_archived(attempt.exam.examquestionpool, attempt.revision).fileinfo
                )
            }
            if not compare_exams(pools, primary_key="None")[0]:
                form.add_error("refresh", _("Cannot update, the exam files are incompatible"))
                return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

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

@ensure_responsible
def refresh_attempts(request, course, instance, content):

    if request.method == "POST":
        form = ExamAttemptRefreshForm(request.POST)
        if not form.is_valid():
            errors = form.errors.get_json_data()
            return JsonResponse({"errors": errors}, status=400)

        pools = {"None": load_pool_file(content.examquestionpool.fileinfo)}
        attempts = MultipleQuestionExamAttempt.objects.filter(
            exam=content,
            instance=instance,
            open_from__gt=form.cleaned_data["start"]
        )
        if end := form.cleaned_data.get("end"):
            attempts = attempts.filter(open_to__lt=end)

        for attempt in attempts:
            if attempt.revision not in pools:
                pools[attempt.revision] = load_pool_file(
                    get_single_archived(attempt.exam.examquestionpool, attempt.revision).fileinfo
                )

        if not compare_exams(pools, primary_key="None")[0]:
            form.add_error(None, _("Cannot update, some exam files are incompatible"))
            return JsonResponse({"errors": form.errors.get_json_data()}, status=400)

        updated = attempts.update(revision=find_latest_version(attempt.exam).revision_id)
        return JsonResponse({
            "status": "ok",
            "status_string": _("Refreshed {count} attempts").format(count=updated),
        })

    form = ExamAttemptRefreshForm()
    form_t = loader.get_template("courses/base-edit-form.html")
    form_c = {
        "form_object": form,
        "submit_url": request.path,
        "html_id": f"refresh-attempts-form",
        "html_class": "exam-management-form",
    }
    return HttpResponse(form_t.render(form_c, request))

# ^
# |
# ATTEMPT MANAGEMENT
# CONFIGURATION VIEWS
# |
# v

@ensure_staff
def edit_question_pool(request, course, instance, content):
    try:
        question_pool = content.examquestionpool
    except ObjectDoesNotExist:
        question_pool = None

    def post_save(pool, form):
        pool.exercise = content

    return process_modelform(
        request,
        QuestionPoolForm,
        question_pool,
        form_id=f"{content.slug}-question-pool-form",
        comment=f"Change {content.slug} question pool",
        parent=content,
        post_save_cb=post_save,
    )

def download_question_pool(request, exercise_id, field_name, filename):
    return download_exercise_backend(
        request, exercise_id, field_name, filename, ExamQuestionPool
    )
