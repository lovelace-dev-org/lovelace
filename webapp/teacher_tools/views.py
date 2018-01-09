import os.path
import tempfile
import zipfile

from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext as _
from django.template import loader

from utils.access import determine_access, is_course_staff

from courses.models import *



# Create your views here.

def download_answers(request, course_slug, instance_slug, content_slug):
    
    content = ContentPage.objects.get(slug=content_slug)
    
    if not determine_access(request.user, content, responsible_only=True):
        return HttpResponseForbidden(_("Only course main responsible teachers are allowed to download answer files."))
    
    temp_storage = tempfile.TemporaryFile()
    content_zip = zipfile.ZipFile(temp_storage ,"w")
    
    files = FileUploadExerciseReturnFile.objects.filter(
        answer__exercise__slug=content_slug,
        answer__instance__course__slug=course_slug,
        answer__instance__slug=instance_slug,
    ).values_list("fileinfo", flat=True)
    
    errors = []
    
    for fileinfo in files:
        parts = fileinfo.split("/")
        
        fs_path = os.path.join(getattr(settings, "PRIVATE_STORAGE_FS_PATH", settings.MEDIA_ROOT), fileinfo)
        
        try:
            content_zip.write(fs_path.encode("utf-8"), "/".join((parts[2], parts[1], parts[3], parts[4])))
        except (IndexError, OSError) as e:
            errors.append(fileinfo)    
            
    if errors:
        error_str = "Zipping failed for these files:\n\n" + "\n".join(errors)    
        content_zip.writestr("{}/error_manifest".format(parts[2]), error_str)
    
    content_zip.close()
    
    temp_storage.seek(0)
    
    response = HttpResponse(temp_storage.read(), content_type="application/zip")
    response["Content-Disposition"] = "attachment; filename={}_answers.zip".format(content_slug)
    return response
    
    
def manage_enrollments(request, course_slug, instance_slug):
    
    try:
        instance_object = CourseInstance.objects.get(slug=instance_slug)
    except CourseInstance.DoesNotExist as e:
        return HttpNotFound(_("This course instance does not exist."))
    
    if not is_course_staff(request.user, instance_object, responsible_only=True):
        return HttpResponseForbidden(_("Only course main resopnsible teachers are allowed to manage enrollments."))
    
    if request.method == "POST":
        form = request.POST
        
        response = {}
        
        if "username" in form:
            username = form.get("username")
            try:
                enrollment = CourseEnrollment.objects.get(student__username=username)
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
            
            enrollments = CourseEnrollment.objects.filter(student__username__in=usernames)
            
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
            
            enrollment = CourseEnrollment.objects.get(student=user)
            enrollment_list.append((user, enrollment))
            
        t = loader.get_template("teacher_tools/manage_enrollments.html")
        c = {
            "course": course_slug,
            "instance": instance_object,
            "enrollments": enrollment_list,
        }
        
        return HttpResponse(t.render(c, request))
        
        
    
    
    
    
    
    
    
    
    
        
    
   
    
    
    
