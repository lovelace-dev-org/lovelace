import os
import random
import routine_exercise.tasks as routine_tasks

from django.db import transaction
from django.http import JsonResponse, HttpResponse
from django.utils import translation
from django.utils.translation import gettext as _

from lovelace.celery import app as celery_app

from courses import markupparser

from routine_exercise.models import *
from utils.access import ensure_enrolled_or_staff, determine_access
from utils.archive import find_version_with_filename, get_archived_instances, get_single_archived
from utils.exercise import render_json_feedback, update_completion
from utils.files import generate_download_response, get_file_contents_b64
from utils.notify import send_error_report

def _question_context_data(request, course, instance, question):
    template_context = {
        'course_slug': course.slug,
        'instance_slug': instance.slug,
    }
    rendered_text = question.template.content.format(**question.generated_json["formatdict"])
    marked_text = "".join(markupparser.MarkupParser.parse(rendered_text, request, template_context)).strip()

    data = {
        "task": "generate",
        "ready": True,
        "question": marked_text,
        "data": question.generated_json
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
            routineexerciseanswer=None
        )
        question = RoutineExerciseQuestion(
            instance=instance,
            exercise=content,
            user=user,
            revision=revision,
            language_code=lang_code,
            question_class=data["question_class"],
            generated_json=data,
            date_generated=datetime.datetime.now(),
            template=template
        )
        question.save()
    return question

def _save_evaluation(user, instance, content, task_id, task_info):
    try:
        answer = RoutineExerciseAnswer.objects.get(
            task_id=task_id
        )
    except RoutineExerciseAnswer.DoesNotExist as e:
        return HttpResponse(404)

    answer.correct = task_info["data"]["correct"]
    answer.save()
    progress = RoutineExerciseProgress.objects.get(
        instance=instance,
        exercise=content,
        user=user
    )
    progress.progress = task_info["data"]["progress"]
    progress.completed = task_info["data"]["completed"]
    progress.save()
    return progress

def _routine_payload(user, instance, content, revision, progress, answer=None):
    payload = {
        "resources": {
            "backends": []
        },
        "meta": {
        },
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
        
        payload["resources"]["backends"].append({
            "name": backend.filename,
            "handle": backend.fileinfo.name,
            "content": get_file_contents_b64(backend)
        })

    answers = RoutineExerciseAnswer.objects.filter(
        question__user=user,
        question__instance=instance,
        question__exercise=content
    ).order_by("answer_date")
    
    payload["meta"]["history"] = [(answer.question.question_class, answer.correct) for answer in answers]
    payload["meta"]["completed"] = progress.completed
    payload["meta"]["progress"] = progress.progress
    
    if answer is not None:
        payload["answer"] = answer.given_answer
        payload["question"] = {
            "class": answer.question.question_class,
            "data": answer.question.generated_json
        }
    
    return payload

@ensure_enrolled_or_staff
def get_routine_question(request, course, instance, content, revision):
    content = content.get_type_object()
    lang_code = translation.get_language()
    if revision == "head":
        revision = None

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
        revision=revision,
        routineexerciseanswer=None
    ).first()
    
    if question is None:
        payload = _routine_payload(request.user, instance, content, revision, progress)
        task = routine_tasks.generate_question.delay(
            payload
        )
        progress_url = reverse(
            "routine_exercise:task_progress",
            kwargs={
                "course": course,
                "instance": instance,
                "content": content,
                "task_id": task.id
            }
        )
        data = {
            "task": "generate",
            "ready": False,
            "redirect": progress_url
        }
        return JsonResponse(data)

    try:
        data = _question_context_data(request, course, instance, question)
    except Exception as e:
        return JsonResponse({"error": _(
            "Question retrieval failed. Contact teaching staff (reason: %s)"
        ) % e})
    data["progress"] = progress.progress
    return JsonResponse(data)

@ensure_enrolled_or_staff
def routine_progress(request, course, instance, content, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        info = task.info
        if info.get("status", "fail") == "fail":
            try:
                answer_id = RoutineExerciseAnswer.objects.get(task_id=task_id).id
            except RoutineExercise.DoesNotExist:
                answer_id = 0

            answer_url = reverse("courses:show_answers", kwargs={
                "user": request.user,
                "course": course,
                "instance": instance,
                "exercise": content
            }) + "#" + str(answer_id)
            send_error_report(instance, content, info["revision"], [info["error"]], answer_url)
            data = {
                "errors": _("Operation failed. Course staff has been notified.")
            }
            return JsonResponse(data)

        if info["task"] == "generate":
            question = _save_question(request.user, instance, content, info, info["data"])
            try:
                data = _question_context_data(request, course, instance, question)
            except Exception as e:
                return JsonResponse({"error": _(
                    "Question retrieval failed. Contact teaching staff (reason: %s)"
                ) % e})
            progress = RoutineExerciseProgress.objects.get(
                instance=instance,
                exercise=content,
                user=request.user
            )
            progress.progress = info["data"]["progress"]
            progress.save()
            data["progress"] = progress.progress
            return JsonResponse(data)
        elif info["task"] == "check":
            progress = _save_evaluation(request.user, instance, content, task_id, info)
            data = render_json_feedback(info["data"]["log"], request, course, instance)
            if progress.completed:
                data["evaluation"] = True
                data["score"] = content.default_points
                update_completion(content, instance, request.user, data)
            data["next_instance"] = True
            data["progress"] = progress.progress
            next_question = info["data"].get("next")
            if next_question:
                _save_question(request.user, instance, content, info, info["data"]["next"])

            return JsonResponse(data)
    else:
        progress_url = reverse(
            "routine_exercise:task_progress",
            kwargs={
                "course": course,
                "instance": instance,
                "content": content,
                "task_id": task.id
            }
        )
        data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
        return JsonResponse(data)

@ensure_enrolled_or_staff
def check_routine_question(request, course, instance, content, revision):
    if request.method != "POST":
        return HttpResponseNotAllowed(['POST'])

    content = content.get_type_object()
    lang_code = translation.get_language()
    if revision == "head":
        revision = None

    try:
        question = RoutineExerciseQuestion.objects.get(
            routineexerciseanswer=None,
            user=request.user,
            instance=instance,
            exercise=content,
            revision=revision,
        )
    except RoutineExerciseQuestion.DoesNotExist as e:
        return HttpResponse(_("You don't have an unanswered question for this exercise."), status=404)

    answer_str = request.POST["answer"]
    answer = RoutineExerciseAnswer(
        question=question,
        answer_date=datetime.datetime.now(),
        given_answer=answer_str
    )
    progress = RoutineExerciseProgress.objects.get(
        user=request.user,
        instance=instance,
        exercise=content,
    )
    payload = _routine_payload(request.user, instance, content, revision, progress, answer)

    task = routine_tasks.check_answer.delay(
        payload
    )
    
    answer.task_id = task.task_id
    answer.save()

    progress_url = reverse(
        "routine_exercise:task_progress",
        kwargs={
            "course": course,
            "instance": instance,
            "content": content,
            "task_id": task.id
        }
    )
    data = {
        "task": "check",
        "ready": False,
        "redirect": progress_url
    }
    return JsonResponse(data)


# TODO: limit to owner and course staff
def download_routine_exercise_backend(request, exercise_id, field_name, filename):
    
    try:
        exercise_object = RoutineExercise.objects.get(id=exercise_id)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This exercise does't exist"))
            
    if not determine_access(request.user, exercise_object):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download files through this interface."))

    fileobjects = RoutineExerciseBackendFile.objects.filter(exercise=exercise_object)
    try:
        for fileobject in fileobjects:
            if filename == os.path.basename(getattr(fileobject, field_name).name):
                fs_path = os.path.join(settings.PRIVATE_STORAGE_FS_PATH, getattr(fileobject, field_name).name)
                break
            else:
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















































