import courses.models as cm

def get_group_members(user, instance):
    try:
        group = cm.StudentGroup.objects.get(
            instance=instance,
            members=user
        )
    except cm.StudentGroup.DoesNotExist:
        return cm.User.objects.none()
    
    return group.members.get_queryset().exclude(id=user.id)
    
    
    