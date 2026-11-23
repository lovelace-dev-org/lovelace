import datetime
from functools import total_ordering, wraps


from django.db.models import Q
from django.conf import settings
from django.http import HttpResponseForbidden
from django.utils.translation import gettext as _
from reversion.models import Version
import courses.models as cm

def get_permissions(user):
    return cm.CourseStaffPermission.objects.filter(
        Q(end_time=None) | Q(end_time__gt=datetime.datetime.now()),
        user=user,
        start_time__lt=datetime.datetime.now()
    )

def get_permission(user, instance):
    return cm.CourseStaffPermission.objects.filter(
        Q(end_time=None) | Q(end_time__gt=datetime.datetime.now()),
        instance=instance,
        user=user,
        start_time__lt=datetime.datetime.now()
    ).first()


def determine_access(user, model_inst, responsible_only=False):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    permissions = get_permissions(user).filter(
        instance__course=model_inst.origin
    )
    if responsible_only:
        permissions = permissions.filter(role="teacher")

    if permissions:
        return True

    return False


def is_course_staff(user, instance, responsible_only=False):
    """
    Determines whether the user is part of the staff of a course.
    Superuser, responsible teacher, and any user in the staff group
    of the course are considered course staff. With responsible_only,
    staff group members are not included.
    """

    print("DEPRECATION WARNING: is_course_staff is deprecated, use get_staff_role instead")

    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    try:
        permission = get_permissions(user).get(instance=instance)
    except cm.CourseStaffPermission.DoesNotExist:
        return False

    if not responsible_only:
        return True

    return permission.permit_management


def get_staff_role(user, instance):
    if not user.is_authenticated:
        return None

    if user.is_superuser:
        return cm.CourseStaffPermission.superuser_role(user, instance)

    try:
        return get_permissions(user).get(instance=instance)
    except cm.CourseStaffPermission.DoesNotExist:
        return None

def accessible_courses(user):
    courses = cm.Course.objects.all()
    if user.is_superuser:
        return courses

    permissions = user.coursestaffpermission_set.get_queryset()
    if permissions:
        courses = set(permission.instance.course_id for permission in permissions)
        return cm.Course.objects.filter(id__in=courses)

    return cm.Course.objects.none()

def check_permission(user, instance, attr):
    if permission := get_permission(user, instance):
        if getattr(permission, attr, False):
            return True

    return False



# ^
# |
# UTILITY FUNCTIONS
# DECORATORS
# |
# v

def block_in_exam_mode(function):
    """
    Decorator to prevent access to this view when the platform is in exam mode.
    """

    @wraps(function)
    def wrap(*args, **kwargs):
        if settings.EXAM_MODE:
            return HttpResponseForbidden(_("This view is not accessible in exam mode"))
        return function(*args, **kwargs)

    return wrap

def ensure_logged_in(function):
    """
    Decorator to limit a view to logged in users. Returns HttpResponseForbidden
    if the user has not been authenticated.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated:
            return function(request, *args, **kwargs)
        return HttpResponseForbidden(_("This view is limited to logged in users."))

    return wrap

def ensure_admin(function):
    """
    Decorator for limiting access to a function to admin users only. Returns
    HttpResponseForbidden instead of calling the wrapped function if the user
    is not ad admin.
    """

    @wraps(function)
    def wrap(request, *args, **kwargs):
        if request.user.is_superuser:
            return function(request, *args, **kwargs)
        return HttpResponseForbidden(_("This view is limited to admins."))

    return wrap

def ensure_permission(attr):
    """
    Decorator for limiting access to a view based on the accessing user having
    the correct permission. Returns HttpResponseForbidden if permission object doesn't
    exist, or doesn't have the required permission set to True.
    """

    def decorator(function):

        @wraps(function)
        def wrap(request, course, instance, *args, **kwargs):
            if permission := get_staff_role(request.user, instance):
                if getattr(permission, attr):
                    return function(request, course, instance, *args, **kwargs)
            return HttpResponseForbidden(_("This view is limited to course staff."))

        return wrap
    return decorator

def ensure_enrolled_or_permission(attr):

    def decorator(function):

        @wraps(function)
        def wrap(request, user, course, instance, *args, **kwargs):
            try:
                if cm.CourseEnrollment.objects.get(
                    instance=instance, student=request.user
                ).is_enrolled():
                    return function(request, course, instance, *args, **kwargs)
            except cm.CourseEnrollment.DoesNotExist:
                pass
            except TypeError:
                return HttpResponseForbidden(_("You must be enrolled to perform this action."))

            if permission := get_staff_role(request.user, instance):
                if getattr(permission, attr):
                    return function(request, course, instance, *args, **kwargs)
            return HttpResponseForbidden(_("This view is limited to course staff."))
        return wrap
    return decorator


def ensure_owner_or_permission(attr):
    """
    Decorator for limiting access to a view based on the accessing user either owning it or having
    the correct permission. Returns HttpResponseForbidden if permission object doesn't
    exist, or doesn't have the required permission set to True.
    """

    def decorator(function):

        @wraps(function)
        def wrap(request, user, course, instance, *args, **kwargs):
            if request.user == user:
                return function(request, user, course, instance, *args, **kwargs)
            if permission := get_staff_role(request.user, instance):
                if getattr(permission, attr):
                    return function(request, course, instance, *args, **kwargs)
            return HttpResponseForbidden(_("This view is limited to course staff."))
        return wrap
    return decorator
