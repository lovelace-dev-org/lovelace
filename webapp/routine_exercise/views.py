from collections import defaultdict
import datetime
import os
import random

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
    HttpResponseNotFound,
    JsonResponse,
)
from django.template import loader
from django.urls import reverse
from django.utils import translation
from django.utils.translation import gettext as _

from reversion import revisions as reversion

from lovelace import plugins as lovelace_plugins
from lovelace.celery import app as celery_app

from courses import markupparser
import courses.models as cm
import courses.tasks as rpc_tasks

from routine_exercise.models import (
    RoutineExercise,
    RoutineExerciseAnswer,
    RoutineExerciseBackendFile,
    RoutineExerciseProgress,
    RoutineExerciseQuestion,
    RoutineExerciseTemplate,
)
import routine_exercise.tasks as routine_tasks
from routine_exercise.forms import BackendForm, CommandForm, TemplateForm

from utils.access import ensure_enrolled_or_staff, ensure_staff, determine_access
from utils.archive import (
    find_version_with_filename, get_archived_instances, get_single_archived,
    squash_revisions
)
from utils.content import download_exercise_backend
from utils.exercise import render_json_feedback, update_completion
from utils.files import generate_download_response, get_file_contents_b64
from utils.management import process_modelform, process_delete_confirm_form
from utils.notify import send_error_report


def _question_context_data(request, course, instance, question):
    template_context = {
        "course_slug": course.slug,
        "instance_slug": instance.slug,
    }
    rendered_text = question.template.content.format(**question.generated_json["formatdict"])
    parser = markupparser.MarkupParser()
    marked_text = "".join(
        block[1] for block in parser.parse(rendered_text, request, template_context)
    ).strip()

    data = {
        "task": "generate",
        "ready": True,
        "question": marked_text,
        "data": question.generated_json,
    }
    return data


def _save_question(user, instance, content, task_info, data):
    lang_code = translation.get_language()
    revision = instance.embeddedlink_set.get_queryset().get(embedded_page=content).revision
    templates = RoutineExerciseTemplate.objects.filter(
        exercise=content,
        question_class=data["question_class"],
    )
    pick = random.randint(0, templates.count() - 1)
    template = templates.all()[pick]
    with transaction.atomic():
        RoutineExerciseQuestion.objects.filter(
            instance=instance,
            exercise=content,
            user=user,
            revision=revision,
            routineexerciseanswer=None,
        ).delete()
        question = RoutineExerciseQuestion(
            instance=instance,
            exercise=content,
            user=user,
            revision=revision,
            language_code=lang_code,
            question_class=data["question_class"],
            generated_json=data,
            date_generated=datetime.datetime.now(),
            template=template,
        )
        question.save()
    return question


def _save_evaluation(user, instance, content, task_id, task_info):
    try:
        answer = RoutineExerciseAnswer.objects.get(task_id=task_id)
    except RoutineExerciseAnswer.DoesNotExist as e:
        return HttpResponse(404)

    answer.correct = task_info["data"]["correct"]
    answer.save()
    progress = RoutineExerciseProgress.objects.get(instance=instance, exercise=content, user=user)
    progress.progress = task_info["data"]["progress"]
    progress.completed = task_info["data"]["completed"]
    progress.points = task_info["data"]["score"]
    progress.max_points = task_info["data"]["max"]
    progress.save()
    return progress


def _routine_payload(user, instance, content, revision, progress, answer=None):
    payload = {
        "resources": {"backends": []},
        "meta": {},
    }

    if revision is not None:
        archived = get_archived_instances(content, revision)
        backends = archived["routineexercisebackendfile_set"]
        command = archived["routineexercisebackendcommand"]
    else:
        backends = content.routineexercisebackendfile_set.get_queryset()
        command = content.routineexercisebackendcommand

    payload["command"] = command.command

    for backend in backends:
        if revision is not None:
            backend = get_single_archived(backend, revision)

        payload["resources"]["backends"].append(
            {
                "name": backend.filename,
                "handle": backend.fileinfo.name,
                "content": get_file_contents_b64(backend),
            }
        )

    answers = RoutineExerciseAnswer.objects.filter(
        question__user=user, question__instance=instance, question__exercise=content
    ).order_by("answer_date")

    payload["meta"]["history"] = [
        (answer.question.question_class, answer.correct) for answer in answers
    ]
    payload["meta"]["completed"] = progress.completed
    payload["meta"]["progress"] = progress.progress

    if answer is not None:
        payload["answer"] = answer.given_answer
        payload["question"] = {
            "class": answer.question.question_class,
            "data": answer.question.generated_json,
        }

    return payload


@ensure_enrolled_or_staff
def get_routine_question(request, course, instance, parent, content):
    content = content.get_type_object()
    embed_link = cm.EmbeddedLink.objects.get(
        embedded_page=content, instance=instance, parent=parent
    )

    try:
        progress = RoutineExerciseProgress.objects.get(
            user=request.user,
            instance=instance,
            exercise=content,
        )
    except RoutineExerciseProgress.DoesNotExist as e:
        progress = RoutineExerciseProgress(
            user=request.user,
            instance=instance,
            exercise=content,
        )
        progress.save()

    question = RoutineExerciseQuestion.objects.filter(
        user=request.user,
        instance=instance,
        exercise=content,
        revision=embed_link.revision,
        routineexerciseanswer=None,
    ).first()

    if question is None:
        celery_status = rpc_tasks.get_celery_worker_status()
        if "errors" in celery_status:
            return JsonResponse(
                {
                    "error": _(
                        "Question retrieval failed. Contact teaching staff (reason: {e})"
                    ).format(e=celery_status["errors"])
                }
            )

        payload = _routine_payload(request.user, instance, content, embed_link.revision, progress)
        task = routine_tasks.generate_question.delay(payload)
        progress_url = reverse(
            "routine_exercise:task_progress",
            kwargs={
                "course": course,
                "instance": instance,
                "content": content,
                "parent": parent,
                "task_id": task.id
            },
        )
        data = {"task": "generate", "ready": False, "redirect": progress_url}
        return JsonResponse(data)

    try:
        data = _question_context_data(request, course, instance, question)
    except Exception as e:
        return JsonResponse(
            {
                "error": _(
                    "Question retrieval failed. Contact teaching staff (reason: {e})"
                ).format(e=e)
            }
        )
    data["progress"] = progress.progress
    return JsonResponse(data)


@ensure_enrolled_or_staff
def routine_progress(request, course, instance, parent, content, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if not task.ready():
        progress_url = reverse(
            "routine_exercise:task_progress",
            kwargs={
                "course": course,
                "instance": instance,
                "content": content,
                "parent": parent,
                "task_id": task.id},
        )
        data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
        return JsonResponse(data)

    info = task.info
    if info.get("status", "fail") == "fail":
        try:
            answer_id = RoutineExerciseAnswer.objects.get(task_id=task_id).id
        except RoutineExerciseAnswer.DoesNotExist:
            answer_id = 0

        answer_url = (
            reverse(
                "courses:show_answers",
                kwargs={
                    "user": request.user,
                    "course": course,
                    "instance": instance,
                    "parent": parent,
                    "exercise": content,
                },
            )
            + "#"
            + str(answer_id)
        )

        revision = instance.embeddedlink_set.get_queryset().get(embedded_page=content).revision
        send_error_report(
            instance, content, revision, [info["error"]], request.build_absolute_uri(answer_url)
        )
        data = {"errors": _("Operation failed. Course staff has been notified.")}
        return JsonResponse(data)

    if info.get("status") == "timeout":
        data = {
            "errors": _(
                "Operation timed out. "
                "Check that your code doesn't have input prompts unless requested "
                "and doesn't cause infinite loops."
            )
        }
        return JsonResponse(data)


    if info["task"] == "generate":
        if info["data"].get("over", False):
            return JsonResponse({"error": _("No more questions available.")})

        question = _save_question(request.user, instance, content, info, info["data"]["next"])
        try:
            data = _question_context_data(request, course, instance, question)
        except Exception as e:
            return JsonResponse(
                {
                    "error": _(
                        "Question retrieval failed. Contact teaching staff (reason: {e})"
                    ).format(e=e)
                }
            )
        progress = RoutineExerciseProgress.objects.get(
            instance=instance, exercise=content, user=request.user
        )
        progress.progress = info["data"]["progress"]
        progress.save()
        data["progress"] = progress.progress
        return JsonResponse(data)

    if info["task"] == "check":
        try:
            answer = RoutineExerciseAnswer.objects.get(task_id=task_id)
        except RoutineExercise.DoesNotExist:
            return JsonResponse({"error": _("Unable to find matching answer.")})

        embed_link = instance.embeddedlink_set.get_queryset().get(
            embedded_page=content, parent=parent
        )

        progress = _save_evaluation(request.user, instance, content, task_id, info)
        data = render_json_feedback(
            info["data"]["log"], request, course, instance, embed_link, content, answer.id
        )
        data["points"] = info["data"]["score"]
        data["max"] = info["data"]["max"]

        if progress.completed:
            data["evaluation"] = True
            update_completion(content, embed_link, instance, request.user, data, answer.answer_date)
            total_evaluation, quotient = content.get_user_evaluation(request.user, instance)
            data["score"] = f"{quotient * embed_link.default_points:.2f}"
            data["total_evaluation"] = total_evaluation
        else:
            data["score"] = f"{0:.2f}"
            data["total_evaluation"] = "ongoing"
        data["next_instance"] = True
        data["progress"] = progress.progress

        data["extra_callbacks"] = []

        for module in lovelace_plugins["exercise-triggers"]:
            data["extra_callbacks"].extend(module.includes.get_exercise_trigger_callbacks(
                instance, content, data
            ))

        next_question = info["data"].get("next")
        if next_question:
            _save_question(request.user, instance, content, info, info["data"]["next"])

        return JsonResponse(data)

    return JsonResponse({"error": _("Invalid task type.")})


@ensure_enrolled_or_staff
def check_routine_question(request, course, instance, parent, content):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    embed_link = cm.EmbeddedLink.objects.get(
        embedded_page=content, instance=instance, parent=parent
    )
    content = content.get_type_object()
    revision = embed_link.revision

    try:
        question = RoutineExerciseQuestion.objects.get(
            routineexerciseanswer=None,
            user=request.user,
            instance=instance,
            exercise=content,
            revision=revision,
        )
    except RoutineExerciseQuestion.DoesNotExist as e:
        return HttpResponse(
            _("You don't have an unanswered question for this exercise."), status=404
        )

    answer_str = request.POST["answer"]
    answer = RoutineExerciseAnswer(
        question=question, answer_date=datetime.datetime.now(), given_answer=answer_str
    )
    progress = RoutineExerciseProgress.objects.get(
        user=request.user,
        instance=instance,
        exercise=content,
    )
    payload = _routine_payload(request.user, instance, content, revision, progress, answer)

    celery_status = rpc_tasks.get_celery_worker_status()
    if "errors" in celery_status:
        return HttpResponse(
            _("Cannot connect to backend."), status=400
        )

    task = routine_tasks.check_answer.delay(payload)

    answer.task_id = task.task_id
    answer.save()

    progress_url = reverse(
        "routine_exercise:task_progress",
        kwargs={
            "course": course,
            "instance": instance,
            "parent": parent,
            "content": content,
            "task_id": task.id,
        },
    )
    data = {"task": "check", "ready": False, "redirect": progress_url}
    return JsonResponse(data)

# ^
# |
# CHECKING VIEWS
# CONFIGURATION VIEWS
# |
# v


@ensure_staff
def routine_backend_panel(request, course, instance, content):
    backends = content.routineexercisebackendfile_set.get_queryset()
    c = {
        "course": course,
        "instance": instance,
        "content": content,
        "backends": backends,
        "panel_refresh_url": request.path,
    }
    t = loader.get_template("routine_exercise/routine-backend-panel.html")
    return HttpResponse(t.render(c, request))

@ensure_staff
def edit_backend(request, course, instance, content, filename):
    backend = RoutineExerciseBackendFile.objects.get(
        exercise=content,
        filename=filename,
    )

    return process_modelform(
        request,
        BackendForm,
        backend,
        form_id=f"{content.slug}-routine-backend-form",
        comment=f"Change {content.slug} backend file {backend.filename}",
        parent=content,
        extra_response={
            "refresh": True
        }
    )

@ensure_staff
def delete_backend(request, course, instance, content, filename):
    backend = RoutineExerciseBackendFile.objects.get(
        exercise=content,
        filename=filename,
    )

    def delete_success(form):
        with reversion.create_revision():
            backend.delete()

            # Save the content to include it in the revision
            content.save()
            reversion.set_user(request.user)
            reversion.set_comment(
                f"Delete exercise {content.slug} backend {backend.filename}"
            )
        squash_revisions(content, 1)

    return process_delete_confirm_form(
        request,
        delete_success,
        extra_context={
            "submit_override": "editing.submit_form",
        },
        extra_response={
            "refresh": True
        }
    )

@ensure_staff
def add_backend(request, course, instance, content):

    def post_save(backend, form):
        backend.exercise = content

    return process_modelform(
        request,
        BackendForm,
        None,
        form_id=f"{content.slug}-routine-backend-form",
        comment=f"Add {content.slug} backend file",
        parent=content,
        post_save_cb=post_save,
        extra_response={
            "refresh": True
        }
    )

@ensure_staff
def edit_command(request, course, instance, content):

    try:
        command = content.routineexercisebackendcommand
    except ObjectDoesNotExist:
        command = None

    def post_save(command, form):
        command.exercise = content

    return process_modelform(
        request,
        CommandForm,
        command,
        form_id=f"{content.slug}-routine-command-form",
        comment=f"Change {content.slug} backend command",
        parent=content,
        post_save_cb=post_save,
        extra_response={
            "refresh": True
        }
    )

@ensure_staff
def routine_template_panel(request, course, instance, content):
    templates = content.routineexercisetemplate_set.get_queryset().order_by(
        "question_class", "variant"
    )
    by_qc = defaultdict(list)
    for template in templates:
        by_qc[template.question_class].append(template)

    c = {
        "course": course,
        "instance": instance,
        "content": content,
        "question_classes": by_qc.items(),
        "panel_refresh_url": request.path,
    }
    t = loader.get_template("routine_exercise/routine-template-panel.html")
    return HttpResponse(t.render(c, request))

@ensure_staff
def edit_template(request, course, instance, content, qc, variant):
    template = RoutineExerciseTemplate.objects.get(
        exercise=content,
        question_class=qc,
        variant=variant,
    )

    return process_modelform(
        request,
        TemplateForm,
        template,
        form_id=f"{content.slug}-routine-template-form",
        comment=f"Change {content.slug} template {qc}-{variant}",
        parent=content,
        extra_response={
            "refresh": True
        }
    )

@ensure_staff
def delete_template(request, course, instance, content, qc, variant):
    template = RoutineExerciseTemplate.objects.get(
        exercise=content,
        question_class=qc,
        variant=variant,
    )

    def delete_success(form):
        with reversion.create_revision():
            template.delete()

            # Save the content to include it in the revision
            content.save()
            reversion.set_user(request.user)
            reversion.set_comment(
                f"Delete exercise {content.slug} template {qc}-{variant}"
            )
        squash_revisions(content, 1)

    return process_delete_confirm_form(
        request,
        delete_success,
        extra_context={
            "submit_override": "editing.submit_form",
        },
        extra_response={
            "refresh": True
        }
    )

@ensure_staff
def add_template(request, course, instance, content, qc):
    def post_save(template, form):
        if last := content.routineexercisetemplate_set.get_queryset().filter(
            question_class=qc
        ).order_by("variant").last():
            variant = last.variant + 1
        else:
            variant = 1

        template.question_class = qc
        template.exercise = content
        template.variant = variant

    return process_modelform(
        request,
        TemplateForm,
        None,
        form_id=f"{content.slug}-routine-template-form",
        comment=f"Add {content.slug} template",
        parent=content,
        post_save_cb=post_save,
        extra_response={
            "refresh": True
        }
    )



def download_routine_exercise_backend(request, exercise_id, field_name, filename):
    return download_exercise_backend(
        request, exercise_id, field_name, filename, RoutineExerciseBackendFile
    )
