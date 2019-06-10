from functools import wraps

from courses.models import CourseEnrollment, CourseInstance, Course
from django.db.models import Q
from django.http import HttpResponseForbidden
from django.utils.translation import ugettext as _
from reversion.models import Version



def determine_access(user, content, responsible_only=False):
    """
    Determines whether user has access to staff only functions of a content
    object. Access is granted if:
    * the user is superuser
    * the user has created/edited the object 
    * the user is the main responsible of a course the content is found in
    * the user is a member of the staff group of a course the content is found 
      in (can be disabled by setting responsible_only to True)
    """    
    
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if user.is_staff:
        if Version.objects.get_for_object(content).filter(revision__user=user).exists():
            return True
        else:
            if responsible_only:
                if Course.objects.filter(
                    Q(courseinstance__contents__content=content) |
                    Q(courseinstance__contents__content__embedded_pages=content)
                ).filter(main_responsible=user):                
                    return True
            else:
                if Course.objects.filter(
                    Q(courseinstance__contents__content=content) |
                    Q(courseinstance__contents__content__embedded_pages=content)
                ).filter(staff_group__user=user):
                    return True
    
    return False

def determine_media_access(user, media):
    
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if user.is_staff:
        if Version.objects.get_for_object(media).filter(revision__user=user).exists():
            return True
        elif media.coursemedialink_set.get_queryset().filter(instance__course__staff_group__user=user).distinct():
            return True            
        
    return False
    

def is_course_staff(user, instance, responsible_only=False):
    
    if not user.is_authenticated:
        return False
    
    if user.is_superuser:
        return True
    
    if user.is_staff:
        if not responsible_only:
            if user in instance.course.staff_group.user_set.get_queryset():
                return True
            
        return user == instance.course.main_responsible
    
    return False

# ^
# |
# UTILITY FUNCTIONS
# DECORATORS
# |
# v
    
def ensure_staff(function):
    @wraps(function)
    def wrap(request, course, instance, *args, **kwargs):
        if is_course_staff(request.user, instance):
            return function(request, course, instance, *args, **kwargs)
        else:
            return HttpResponseForbidden(_("This view is limited to course staff."))    
    return wrap

def ensure_responsible(function):
    @wraps(function)
    def wrap(request, course, instance, *args, **kwargs):
        if is_course_staff(request.user, instance, True):
            return function(request, course, instance, *args, **kwargs)
        else:
            return HttpResponseForbidden(_("This view is limited to main responsible teacher."))
    return wrap

def ensure_enrolled_or_staff(function):
    @wraps(function)
    def wrap(request, course, instance, *args, **kwargs):
        try:
            if CourseEnrollment.objects.get(instance=instance, student=request.user).is_enrolled():
                return function(request, course, instance, *args, **kwargs)
        except:
            pass
        
        if is_course_staff(request.user, instance):
            return function(request, course, instance, *args, **kwargs)

        return HttpResponseForbidden(_("You must be enrolled to perform this action."))
    return wrap

def ensure_owner_or_staff(function):
    @wraps(function)
    def wrap(request, user, course, instance, *args, **kwargs):
        if request.user == user or is_course_staff(request.user, instance):
            return function(request, user, course, instance, *args, **kwargs)
        else:
            return HttpResponseForbidden(_("This view is limited to content owners and staff"))
    return wrap
        
