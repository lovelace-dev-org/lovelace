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
    
    if not user.is_authenticated():
        return False
    
    if user.is_superuser:
        return True
    
    if user.is_staff:
        if Version.objects.get_for_object(content).filter(revision__user=user).exists():
            return True
        else:
            if responsible_only:
                if Course.objects.filter(
                    Q(courseinstance__contents__content=obj) |
                    Q(courseinstance__contents__content__embedded_pages=obj)
                ).filter(main_responsible=user):                
                    return True
            else:
                if Course.objects.filter(
                    Q(courseinstance__contents__content=obj) |
                    Q(courseinstance__contents__content__embedded_pages=obj)
                ).filter(staff_group__user=user):
                    return True
    
    return False

