import csv
import datetime
import os.path
import redis
import tempfile
import zipfile

import teacher_tools.tasks as teacher_tasks

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseGone, JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.template import loader
from django.urls import reverse
from lovelace.celery import app as celery_app

from utils.access import determine_access, is_course_staff, ensure_responsible
from utils.content import get_course_instance_tasks
from utils.notify import send_welcome_email

from courses.models import *
from teacher_tools.utils import *
from teacher_tools.models import *
from teacher_tools.forms import MossnetForm, ReminderForm


def download_answers(request, course, instance, content):

    if not determine_access(request.user, content, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download answer files."))

    files = FileUploadExerciseReturnFile.objects.filter(
        answer__exercise=content,
        answer__instance__course=course,
        answer__instance=instance,
    ).values_list("fileinfo", flat=True)
    
    errors = []
    
    with tempfile.TemporaryFile() as temp_storage:
        with zipfile.ZipFile(temp_storage ,"w") as content_zip:
            for fileinfo in files:
                parts = fileinfo.split(os.path.sep)
                
                fs_path = os.path.join(getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), fileinfo)
                
                try:
                    content_zip.write(fs_path.encode("utf-8"), os.path.join(parts[2], parts[1], parts[4], parts[5]))
                except (IndexError, OSError) as e:
                    errors.append(fileinfo)
                    
            if errors:
                error_str = "Zipping failed for these files:\n\n" + "\n".join(errors)    
                content_zip.writestr("{}/error_manifest".format(parts[2]), error_str)
            
        temp_storage.seek(0)
        response = HttpResponse(temp_storage.read(), content_type="application/zip")
    
    response["Content-Disposition"] = "attachment; filename={}_answers.zip".format(content.slug)
    return response
    
    
def manage_enrollments(request, course, instance):
    
    if not is_course_staff(request.user, instance, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to manage enrollments."))
    
    if request.method == "POST":
        form = request.POST
        
        response = {}
        affected = []
        
        if "username" in form:
            username = form.get("username")
            with transaction.atomic():
                try:
                    enrollment = CourseEnrollment.objects.get(student__username=username, instance=instance)
                except CourseEnrollment.DoesNotExist:
                    response["msg"] = _("Enrollment for the student does not exist.")
                else:                
                    enrollment.enrollment_state = form.get("action").upper()
                    enrollment.save()
                    response["msg"] = _("Enrollment status of {} changed to {}".format(username, form.get("action")))
                    response["new_state"] = form.get("action").upper()
                    response["user"] = username
                    affected.append(username)
            
        else:
            usernames = form.getlist("selected-users")
            action = form.get("action")
            affected = []
            response["users-skipped"] = []
            response["affected-title"] = _("Set enrollment state to {} for the following users.".format(action))            
            response["skipped-title"] = _("The operation was not applicable for these users.")
            response["new_state"] = action.upper()
            
            with transaction.atomic():
                enrollments = CourseEnrollment.objects.filter(student__username__in=usernames, instance=instance)
                
                for enrollment in enrollments:
                    if action == "accepted" and enrollment.enrollment_state == "WAITING":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    elif action == "denied" and enrollment.enrollment_state == "WAITING":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    elif action == "expelled" and enrollment.enrollment_state == "ACCEPTED":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    elif action == "accepted" and enrollment.enrollment_state == "EXPELLED":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        affected.append(enrollment.student.username)
                    else:
                        response["users-skipped"].append(enrollment.student.username)
            
            response["users-affected"] = affected
        
        if form.get("action") == "accepted":
            userlist = User.objects.filter(
                username__in=affected
            )
            send_welcome_email(instance, userlist=userlist)
        
        return JsonResponse(response)
        
    else:        
        users = instance.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")
        
        enrollment_list = []
        
        for user in users:
            
            enrollment = CourseEnrollment.objects.get(student=user, instance=instance)
            enrollment_list.append((user, enrollment))
            
        t = loader.get_template("teacher_tools/manage_enrollments.html")
        c = {
            "course": course,
            "instance": instance,
            "enrollments": enrollment_list,
            "course_staff": True
        }
        
        return HttpResponse(t.render(c, request))
        
@ensure_responsible
def student_course_completion(request, course, instance, user):    

    tasks_by_page = get_course_instance_tasks(instance)
    results_by_page, total_points, total_missing, total_points_available = compile_student_results(user, instance, tasks_by_page)
    t = loader.get_template("teacher_tools/student_completion.html")
    c = {
        "student": user,
        "course": course,
        "instance": instance,
        "results_by_page": results_by_page,
        "total_missing": total_missing,
        "total_points": total_points,
        "total_points_available": total_points_available,
        "course_staff": True
    }
    return HttpResponse(t.render(c, request))

@ensure_responsible
def course_completion_csv(request, course, instance):
    task = teacher_tasks.generate_completion_csv.delay(course.slug, instance.slug)
    return course_completion_csv_progress(request, course, instance, task.id)

@ensure_responsible
def course_completion_csv_progress(request, course, instance, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        download_url = reverse("teacher_tools:completion_csv_download", kwargs={
            "course": course,
            "instance": instance,
            "task_id": task_id
        })
        data = {"state": task.state, "metadata": task.info, "redirect": download_url}
        return JsonResponse(data)
    else:
        progress_url = reverse("teacher_tools:completion_csv_progress", kwargs={
            "course": course,
            "instance": instance,
            "task_id": task_id
        })

        data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
        return JsonResponse(data)

@ensure_responsible
def course_completion_csv_download(request, course, instance, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        csv_str = cache.get(task_id)
        cache.delete(task_id)
        task.forget()
        response = HttpResponse(content=csv_str, content_type="text/csv")
        response["Content-Disposition"] = "attachment; filename={}_completion_{}.csv".format(
            instance.slug,
            datetime.date.today().strftime("%Y-%m-%d")
        )
        return response
    else:
        return HttpResponseGone(
            _("Completion CSV generation (task id: %s) has already been downloaded." % task_id)
        )

@ensure_responsible
def course_completion(request, course, instance):
    users = instance.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")

    t = loader.get_template("teacher_tools/course_completion.html")
    c = {
        "course": course,
        "instance": instance,
        "users": users,
        "course_staff": True
    }

    return HttpResponse(t.render(c, request))

@ensure_responsible
def manage_reminders(request, course, instance):
    saved_template = ReminderTemplate.objects.filter(instance=instance).first()
    if request.method == "POST":
        form = ReminderForm(request.POST, instance=saved_template)
        if form.is_valid():
            if form.cleaned_data["reminder_action"] == "generate":
                if form.cleaned_data.get("save_template"):
                    template = form.save(commit=False)
                    template.instance = instance
                    template.save()

                users = instance.enrolled_users.get_queryset().filter(
                    courseenrollment__enrollment_state="ACCEPTED"
                ).order_by("last_name", "first_name", "username")
                
                tasks_by_page = get_course_instance_tasks(instance, datetime.datetime.now())

                reminder_list = []
                for i, user in enumerate(users, start=1):
                    missing_str = ""
                    missing_count = 0
                    for page, task_links in tasks_by_page:
                        page_stats = check_user_completion(user, task_links, instance, include_links=False)
                        missing_list = []
                        for result in page_stats:
                            if not result["correct"]:
                                missing_list.append(result["eo"])
                                missing_count += 1
                        if missing_list:
                            missing_str += " / ".join(
                                getattr(page, "name_" + code) or "" for code, lang in settings.LANGUAGES
                            ).lstrip(" /")
                            task_strs = []
                            for task in missing_list:
                                task_strs.append(" / ".join(
                                    getattr(task, "name_" + code) or "" for code, lang in settings.LANGUAGES
                                ).lstrip(" /"))
                            missing_str += "\n  " + "\n  ".join(task_strs) + "\n"
                    if missing_str:
                        reminder_data = {
                            "username": user.username,
                            "email": user.email,
                            "first_name": user.first_name,
                            "last_name": user.last_name,
                            "missing_count": missing_count,
                            "missing_str": missing_str
                        }
                        reminder_list.append(reminder_data)

                reminder_cache = {
                    "generated": datetime.date.today().strftime("%Y-%m-%d"),
                    "reminders": reminder_list,
                    "progress": 0
                }
                cache.set("{}_reminders".format(instance.slug), reminder_cache, timeout=settings.REDIS_LONG_EXPIRE)

                return JsonResponse({"reminders": reminder_list, "submit_text": _("Send emails")})

            elif form.cleaned_data["reminder_action"] == "send":
                title = form.cleaned_data.get("title", "")
                header = form.cleaned_data.get("header", "")
                footer = form.cleaned_data.get("footer", "")
                task = teacher_tasks.send_reminder_emails.delay(course.slug, instance.slug, title, header, footer)
                return reminders_progress(request, course, instance, task.id)
    else:
        form = ReminderForm(instance=saved_template)
        reminders = cache.get("{}_reminders".format(instance.slug))
        t = loader.get_template("teacher_tools/manage_reminders.html")
        c = {
            "course": course,
            "instance": instance,
            "form": form,
            "course_staff": True,
            "cached_reminders": reminders
        }
        return HttpResponse(t.render(c, request))

@ensure_responsible
def load_reminders(request, course, instance):
    reminder_cache = cache.get("{}_reminders".format(instance.slug))
    if reminder_cache is None:
        return HttpNotFOund(_("Unable to retrieve cached reminders."))

    return JsonResponse({"reminders": reminder_cache["reminders"], "submit_text": _("Send emails")})

@ensure_responsible
def discard_reminders(request, course, instance):
    cache.delete("{}_reminders".format(instance.slug))
    return JsonResponse({"success": True, "submit_text": _("Generate reminders")})

@ensure_responsible
def reminders_progress(request, course, instance, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        data = {"state": task.state, "metadata": task.info}
        return JsonResponse(data)
    else:
        progress_url = reverse("teacher_tools:reminders_progress", kwargs={
            "course": course,
            "instance": instance,
            "task_id": task_id
        })

        data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
        return JsonResponse(data)

@ensure_responsible
def exercise_plagiarism(request, course, instance, content):
    saved_settings = MossSettings.objects.filter(exercise=content).first()
    other_instances = CourseInstance.objects.filter(course=course).exclude(pk=instance.pk)
    current_url = cache.get("{}_moss_result".format(content.slug))

    if request.method == "POST":
        form = MossnetForm(request.POST, other_instances=other_instances, instance=saved_settings)
        if form.is_valid():
            if form.cleaned_data["save_settings"]:
                settings = form.save(commit=False)
                settings.exercise = content
                settings.save()

            if request.FILES:
                if form.cleaned_data["save_settings"]:
                    MossBaseFile.objects.filter(moss_settings=settings).delete()
                for f in request.FILES.getlist("base_files"):
                    base_file = MossBaseFile(
                        fileinfo=f,
                        exercise=content
                    )
                    if form.cleaned_data["save_settings"]:
                        base_file.moss_settings = settings
                    base_file.save()

            task = teacher_tasks.order_moss_report.delay(course.slug, instance.slug, content.slug, form.cleaned_data)
            return moss_progress(request, course, instance, content, task.id)
    else:
        form = MossnetForm(other_instances=other_instances, instance=saved_settings)
        t = loader.get_template("teacher_tools/exercise_plagiarism.html")
        c = {
            "course": course,
            "instance": instance,
            "exercise": content,
            "course_staff": True,
            "form": form,
            "current_url": current_url
        }
        return HttpResponse(t.render(c, request))

@ensure_responsible
def moss_progress(request, course, instance, content, task_id):
    task = celery_app.AsyncResult(id=task_id)
    if task.ready():
        data = {"state": task.state, "metadata": task.info}
        return JsonResponse(data)
    else:
        progress_url = reverse("teacher_tools:moss_progress", kwargs={
            "course": course,
            "instance": instance,
            "content": content,
            "task_id": task_id
        })
        data = {"state": task.state, "metadata": task.info, "redirect": progress_url}
        return JsonResponse(data)
        