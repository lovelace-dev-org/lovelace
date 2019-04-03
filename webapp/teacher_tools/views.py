import csv
import datetime
import os.path
import tempfile
import zipfile

from django.conf import settings
from django.db import transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.template import loader
from django.urls import reverse

from utils.access import determine_access, is_course_staff

from courses.models import *

def _get_course_instance_tasks(instance):
    
    all_embedded_links = EmbeddedLink.objects.filter(instance=instance).order_by("embedded_page__name")
    
    task_pages = []
    for content_link in instance.contents.all():
        page_task_links = all_embedded_links.filter(parent=content_link.content)
        if page_task_links:
            task_pages.append((content_link.content, page_task_links))
            
    return task_pages

def _check_user_completion(user, task_links, instance):
    results = []
    instance_slug = instance.slug
    course_slug = instance.course.slug
    for link in task_links:
        exercise_obj = link.embedded_page.get_type_object()
        if link.revision is not None:
            exercise_obj = Version.objects.get_for_object(exercise_obj).get(revision=link.revision)._object_version.object

        result = exercise_obj.get_user_evaluation(exercise_obj, user, instance)

        points = 0
        if result == "correct":
            correct = True
            points = exercise_obj.default_points
        elif result == "credited":
            correct = True
        else:
            correct = False
        
        results.append(({
            "eo": exercise_obj,
            "correct": correct,
            "points": points,
            "result": result,
            "answers_link": reverse("courses:show_answers", kwargs={
                "user": user.username,
                "course": course_slug,
                "instance": instance_slug,
                "exercise": exercise_obj.slug
            })
        }))

    return results

def _get_missing_and_points(results):
    missing = 0
    points = 0
    points_available = 0
    for result in results:
        points_available += result["eo"].default_points
        if result["correct"]:
            points += result["eo"].default_points
        else:
            missing += 1
    
    return missing, points, points_available

def _compile_student_results(user, instance, tasks_by_page):
    results_by_page = []
    total_missing = 0
    total_points = 0
    total_points_available = 0
    for page, task_links in tasks_by_page:
        page_stats = _check_user_completion(user, task_links, instance)
        missing, page_points, page_points_available = _get_missing_and_points(page_stats)
        total_points += page_points
        total_points_available += page_points_available
        total_missing += missing
        results_by_page.append({"page": page, "done_count": len(task_links) - missing, "task_count": len(task_links), "points": page_points, "points_available": page_points_available, "tasks_list": page_stats})
    return results_by_page, total_points, total_missing, total_points_available

def download_answers(request, course_slug, instance_slug, content_slug):
    
    content = ContentPage.objects.get(slug=content_slug)
    
    if not determine_access(request.user, content, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download answer files."))
    
    
    files = FileUploadExerciseReturnFile.objects.filter(
        answer__exercise__slug=content_slug,
        answer__instance__course__slug=course_slug,
        answer__instance__slug=instance_slug,
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
    
    response["Content-Disposition"] = "attachment; filename={}_answers.zip".format(content_slug)
    return response
    
    
def manage_enrollments(request, course_slug, instance_slug):
    
    try:
        course_object = Course.objects.get(slug=course_slug)
    except Course.DoesNotExist as e:
        return HttpResponseNotFound(_("This course does not exist."))
    
    try:
        instance_object = CourseInstance.objects.get(slug=instance_slug)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This course instance does not exist."))
    
    if not is_course_staff(request.user, instance_object, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to manage enrollments."))
    
    if request.method == "POST":
        form = request.POST
        
        response = {}
        
        if "username" in form:
            username = form.get("username")
            with transaction.atomic():
                try:
                    enrollment = CourseEnrollment.objects.get(student__username=username, instance=instance_object)
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
            print(usernames)
            action = form.get("action")
            response["users-affected"] = []
            response["users-skipped"] = []
            response["affected-title"] = _("Set enrollment state to {} for the following users.".format(action))            
            response["skipped-title"] = _("The operation was not applicable for these users.")
            response["new_state"] = action.upper()
            
            with transaction.atomic():
                enrollments = CourseEnrollment.objects.filter(student__username__in=usernames, instance=instance_object)
                
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
        users = instance_object.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")
        
        enrollment_list = []
        
        for user in users:
            
            enrollment = CourseEnrollment.objects.get(student=user, instance=instance_object)
            enrollment_list.append((user, enrollment))
            
        t = loader.get_template("teacher_tools/manage_enrollments.html")
        c = {
            "course": course_object,
            "instance": instance_object,
            "enrollments": enrollment_list,
        }
        
        return HttpResponse(t.render(c, request))
        
def student_course_completion(request, course_slug, instance_slug, user):
    
    try:
        course_object = Course.objects.get(slug=course_slug)
    except Course.DoesNotExist as e:
        return HttpResponseNotFound(_("This course does not exist."))
    
    try:
        instance_object = CourseInstance.objects.get(slug=instance_slug)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This course instance does not exist."))
    
    if not is_course_staff(request.user, instance_object, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to view completion stats."))
    
    try:
        user_object = User.objects.get(username=user)
    except UserProfile.DoesNotExist as e:
        return HttpResponseNotFound(_("The student does not exist."))
    
    tasks_by_page = _get_course_instance_tasks(instance_object)
    results_by_page, total_points, total_missing, total_points_available = _compile_student_results(user_object, instance_object, tasks_by_page)
    t = loader.get_template("teacher_tools/student_completion.html")
    c = {
        "user": user_object,
        "course": course_object,
        "instance": instance_object,
        "results_by_page": results_by_page,
        "total_missing": total_missing,
        "total_points": total_points,
        "total_points_available": total_points_available
    }
    
    return HttpResponse(t.render(c, request))


def course_completion_csv(request, course_slug, instance_slug):
    
    try:
        course_object = Course.objects.get(slug=course_slug)
    except Course.DoesNotExist as e:
        return HttpResponseNotFound(_("This course does not exist."))
    
    try:
        instance_object = CourseInstance.objects.get(slug=instance_slug)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This course instance does not exist."))
    
    if not is_course_staff(request.user, instance_object, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to view completion stats."))
    
    users = instance_object.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")
    tasks_by_page = _get_course_instance_tasks(instance_object)
    
    with tempfile.TemporaryFile(mode="w+") as temp_csv:
        writer = csv.writer(temp_csv)
        writer.writerow([
            _("username"), _("last name"), _("first name"), _("student id"),
            _("points"), _("missing"), _("email"), _("results url")
        ])
            
        for user in users:
            results_by_page, total_points, total_missing, total_points_available = _compile_student_results(user, instance_object, tasks_by_page)
            results_url = reverse("teacher_tools:student_completion", kwargs={
                "course_slug": course_slug,
                "instance_slug": instance_slug,
                "user": user.username
            })
            writer.writerow([
                user.username, user.last_name, user.first_name, user.userprofile.student_id,
                total_points, total_missing, user.email, results_url
            ])
        
        temp_csv.seek(0)
        response = HttpResponse(temp_csv.read(), content_type="text/csv")
    
    response["Content-Disposition"] = "attachment; filename={}_completion_{}.csv".format(
        instance_slug,
        datetime.date.today().strftime("%Y-%m-%d")
    )
    return response
                
def course_completion(request, course_slug, instance_slug):
    
    try:
        course_object = Course.objects.get(slug=course_slug)
    except Course.DoesNotExist as e:
        return HttpResponseNotFound(_("This course does not exist."))
    
    try:
        instance_object = CourseInstance.objects.get(slug=instance_slug)
    except CourseInstance.DoesNotExist as e:
        return HttpResponseNotFound(_("This course instance does not exist."))
    
    if not is_course_staff(request.user, instance_object, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to view completion stats."))
    
    users = instance_object.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")
    
    t = loader.get_template("teacher_tools/course_completion.html")
    c = {
        "course": course_object,
        "instance": instance_object,
        "users": users
    }
    
    return HttpResponse(t.render(c, request))
    
        
    
    
    
    
    
    
    
    
    
    
        
    
   
    
    
    
