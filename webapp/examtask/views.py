from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    JsonResponse,
)
from django.shortcuts import render
from django.template import loader
from django.utils.translation import gettext as _

import courses.models as cm

from utils.access import accessible_courses, ensure_staff
from utils.management import (
    CourseContentAdmin,
    process_confirm_form,
    process_modelform,
)
from .models import ExamTaskSettings, ExamTaskAttempt, UserExamTaskAnswer, get_attempt
from .forms import ExamTaskSettingsForm, ExamTaskAttemptForm
from .utils import propagate_attempt

# Create your views here.

@ensure_staff
def exam_task_settings(request, course, instance, parent, content):
    settings, _ = ExamTaskSettings.objects.get_or_create(
        instance=instance,
        task=content,
    )
    courses = accessible_courses(request.user)
    pages = CourseContentAdmin.content_access_list(
        request, cm.ContentPage, origin=course
    ).exclude(content_type__in=["LECTURE", "EXAM_TASK"]).order_by("name")

    form_extra = {
        "accessible_courses": courses,
        "accessible_pages": pages,
        "course": course,
    }

    return process_modelform(
        request,
        ExamTaskSettingsForm,
        settings,
        form_id=f"{content.slug}-exam-settings-form",
        form_extra=form_extra,
        comment=f"Edit {content.slug} exam settings",
        parent=parent,
    )

@ensure_staff
def exam_task_attempts(request, course, instance, parent, content):

    attempts = ExamTaskAttempt.objects.filter(instance=instance, task=content).order_by("start")
    t = loader.get_template("examtask/examtask-attempts.html")
    c = {
        "course": course,
        "instance": instance,
        "parent": parent,
        "content": content,
        "attempts": attempts,
        "panel_refresh_url": request.path,
    }
    return HttpResponse(t.render(c, request))

@ensure_staff
def add_task_attempt(request, course, instance, parent, content):
    def post_save(attempt, form):
        attempt.instance = instance
        attempt.parent = parent
        attempt.task = content
        attempt.save()
        attempt.assign_tasks()
        if form.cleaned_data["propagate"]:
            propagate_attempt(attempt)

    return process_modelform(
        request,
        ExamTaskAttemptForm,
        None,
        form_id=f"{content.slug}-exam-attempt-form",
        comment="Added task attempt",
        post_save_cb=post_save,
        extra_response={"refresh": True},
        form_extra={
            "enrolled_students": instance.enrolled_users.get_queryset(),
        }
    )

@ensure_staff
def edit_task_attempt(request, course, instance, parent, content, attempt):

    def post_save(attempt, form):
        if form.cleaned_data["propagate"]:
            propagate_attempt(attempt)

    return process_modelform(
        request,
        ExamTaskAttemptForm,
        attempt,
        form_id=f"{content.slug}-exam-attempt-form",
        comment="Edited task attempt",
        extra_response={"refresh": True},
        post_save_cb=post_save,
        form_extra={
            "enrolled_students": instance.enrolled_users.get_queryset(),
        }
    )

@ensure_staff
def delete_task_attempt(request, course, instance, parent, content, attempt):

    def delete_success(form):
        attempt.delete()

    return process_confirm_form(
        request, delete_success,
        extra_context={
            "submit_override": "editing.submit_form",
            "disclaimer": _("Delete attempt"),
        },
        extra_response={"refresh": True},
    )

@ensure_staff
def rerandomize_tasks(request, course, instance, parent, content, attempt):

    def confirmed(form):
        attempt.reset_tasks()
        attempt.assign_tasks()

    return process_confirm_form(
        request, confirmed,
        extra_context={
            "submit_override": "editing.submit_form",
            "disclaimer": _("Rerandomize")
        },
        extra_response={"refresh": True},
    )

@ensure_staff
def update_evaluations(request, course, instance, parent, content):

    def confirmed(form):
        link = cm.EmbeddedLink.objects.get(
            instance=instance,
            parent=parent,
            embedded_page=content
        )
        for user in instance.enrolled_users.get_queryset():
            attempt = get_attempt(content, instance, user)
            exercise = attempt.get_user_task(user)
            best_answer = (
                exercise.get_user_answers(exercise, user, instance)
                .order_by("-evaluation__points", "answer_date")
                .first()
            )
            exam_answer = UserExamTaskAnswer.objects.get(task_answer=best_answer)
            evaluation = best_answer.evaluation
            quotient = evaluation.points / evaluation.max_points
            content.update_evaluation(
                link,
                user,
                {
                    "evaluation": evaluation.correct,
                    "points": quotient * link.default_points,
                    "max": link.default_points,
                    "feedback": evaluation.feedback,
                    "evaluator": evaluation.evaluator,
                    "test_results": evaluation.test_results,
                    "suspect": evaluation.suspect,
                    "comment": evaluation.comment,
                },
                exam_answer,
                complete=evaluation.completed,
                overwrite=True,
            )

    return process_confirm_form(
        request, confirmed,
        extra_context={
            "submit_override": "editing.submit_form",
            "disclaimer": _("Update evaluations from assigned tasks")
        },
    )
