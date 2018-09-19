from courses.models import CourseInstance, Course
from django.db.models import Q
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
        elif media.coursemedialink_set.get_queryset().filter(instance__course__staff_group__in=user_groups).distinct():
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
        
            
    
    