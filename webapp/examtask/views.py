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
    process_modelform
)
from .models import ExamTaskSettings, ExamTaskAttempt
from .forms import ExamTaskSettingsForm, ExamTaskAttemptForm

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
    ).exclude(content_type__in=["LECTURE", "EXAM_PAGE"])

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

    attempts = ExamTaskAttempt.objects.filter(instance=instance, task=content)
    t = loader.get_template("examtask/examtask-attempts.html")
    c = {
        "course": course,
        "instance": instance,
        "parent": parent,
        "content": content,
        "attempts": attempts,
    }
    return HttpResponse(t.render(c, request))

@ensure_staff
def add_task_attempt(request, course, instance, content):
    return process_modelform(
        request,
        ExamTaskAttemptForm,
        None,
        form_id=f"{content.slug}-exam-attempt-form",


    )

@ensure_staff
def edit_task_attempt(request, course, instance, content, attempt):
    pass

@ensure_staff
def delete_task_attempt(request, course, instance, content, attempt):
    pass

