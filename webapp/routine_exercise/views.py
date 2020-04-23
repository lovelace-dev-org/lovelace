import random
import routine_exercise.tasks as routine_tasks

from django.http import JsonResponse, HttpResponse
from django.utils import translation
from django.utils.translation import ugettext as _

from lovelace.celery import app as celery_app

from courses import markupparser

from routine_exercise.models import *
from utils.access import ensure_enrolled_or_staff
from utils.exercise import render_json_feedback

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

def _save_question(task_info, data):
    templates = RoutineExerciseTemplate.objects.filter(
        exercise_id=task_info["exercise_id"],
        question_class=data["question_class"],
    )
    pick = random.randint(0, templates.count() - 1)
    template = templates.all()[pick]
    question = RoutineExerciseQuestion(
        instance_id=task_info["instance_id"],
        exercise_id=task_info["exercise_id"],
        user_id=task_info["user_id"],
        language_code=task_info["lang_code"],
        revision=task_info["revision"],
        question_class=data["question_class"],
        generated_json=data,
        date_generated=datetime.datetime.now(),
        template=template
    )
    question.save()
    return question

def _save_evaluation(task_info):
    try:
        answer = RoutineExerciseAnswer.objects.get(
            id=task_info["answer_id"]
        )
    except RoutineExerciseAnswer.DoesNotExist as e:
        return HttpResponse(404)

    answer.correct = task_info["data"]["correct"]
    answer.save()
    progress = RoutineExerciseProgress.objects.get(
        instance_id=task_info["instance_id"],
        exercise_id=task_info["exercise_id"],
        user_id=task_info["user_id"]
    )
    progress.progress = task_info["data"]["progress"]
    progress.completed = task_info["data"]["completed"]
    progress.save()
    return progress

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

    try:
        question = RoutineExerciseQuestion.objects.get(
            user=request.user,
            instance=instance,
            exercise=content,
            revision=revision,
            routineexerciseanswer=None
        )
    except RoutineExerciseQuestion.DoesNotExist as e:
        task = routine_tasks.generate_question.delay(
            request.user.id,
            instance.id,
            content.id,
            lang_code,
            revision,
            progress.completed,
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

    data = _question_context_data(request, course, instance, question)
    data["progress"] = progress.progress
    return JsonResponse(data)

@ensure_enrolled_or_staff
def routine_progress(request, course, instance, content, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        info = task.info

        if instance.id != info["instance_id"] or content.id != info["exercise_id"] or request.user.id != info["user_id"]:
            return HttpResponse(status=409)

        if info["task"] == "generate":
            question = _save_question(info, info["data"])
            data = _question_context_data(request, course, instance, question)
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
            progress = _save_evaluation(info)
            data = render_json_feedback(info["data"]["log"], request, course, instance)
            if progress.completed:
                data["evaluation"] = True
            data["next_instance"] = True
            next_question = info["data"].get("next")
            if next_question:
                _save_question(info, info["data"]["next"])

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
        return HttpResponse(_("You don't have an unanswered question for this exercise.", status=404))

    answer_str = request.POST["answer"]
    answer = RoutineExerciseAnswer(
        question=question,
        date_answered=datetime.datetime.now(),
        given_answer=answer_str
    )
    answer.save()
    task = routine_tasks.check_answer.delay(
        request.user.id,
        instance.id,
        content.id,
        question.id,
        answer.id,
        lang_code,
        revision
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
        "task": "check",
        "ready": False,
        "redirect": progress_url
    }
    return JsonResponse(data)

















































