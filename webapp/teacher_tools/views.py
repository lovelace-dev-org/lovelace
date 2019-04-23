import csv
import datetime
import os.path
import redis
import tempfile
import zipfile

import teacher_tools.tasks as teacher_tasks

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseGone, JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.template import loader
from django.urls import reverse
from lovelace.celery import app as celery_app

from utils.access import determine_access, is_course_staff, ensure_responsible
from utils.content import get_course_instance_tasks

from courses.models import *
from teacher_tools.utils import *


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
                    content_zip.write(fs_path.encode("utf-8"), os.path.join(parts[2], parts[1], parts[3], parts[4]))
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
            
        else:
            usernames = form.getlist("selected-users")
            action = form.get("action")
            response["users-affected"] = []
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
                        response["users-affected"].append(enrollment.student.username)
                    elif action == "denied" and enrollment.enrollment_state == "WAITING":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        response["users-affected"].append(enrollment.student.username)
                    elif action == "expelled" and enrollment.enrollment_state == "ACCEPTED":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        response["users-affected"].append(enrollment.student.username)
                    elif action == "accepted" and enrollment.enrollment_state == "EXPELLED":
                        enrollment.enrollment_state = action.upper()
                        enrollment.save()
                        response["users-affected"].append(enrollment.student.username)
                    else:
                        response["users-skipped"].append(enrollment.student.username)
                    
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
        }
        
        return HttpResponse(t.render(c, request))
        
@ensure_responsible
def student_course_completion(request, course, instance, user):    
    
    tasks_by_page = get_course_instance_tasks(instance)
    results_by_page, total_points, total_missing, total_points_available = compile_student_results(user, instance, tasks_by_page)
    t = loader.get_template("teacher_tools/student_completion.html")
    c = {
        "user": user,
        "course": course,
        "instance": instance,
        "results_by_page": results_by_page,
        "total_missing": total_missing,
        "total_points": total_points,
        "total_points_available": total_points_available
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
        r = redis.StrictRedis(**settings.REDIS_RESULT_CONFIG)
        csv_str = r.get(task_id)
        r.delete(task_id)
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
        "users": users
    }
    
    return HttpResponse(t.render(c, request))
    
    
    
    
    
    
    
    
    
        
    
   
    
    
    
