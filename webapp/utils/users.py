"""
Contains user related utility functions
"""

import courses.models as cm


def get_group_members(user, instance):
    """
    Gets the group members of a user in the given course instance.
    Returns a queryset of users, containing the group's members excluding the
    target user. Returns an empty queryset if the user is not in a group.
    """

    try:
        group = cm.StudentGroup.objects.get(instance=instance, members=user)
    except cm.StudentGroup.DoesNotExist:
        return cm.User.objects.none()

    return group.members.get_queryset().exclude(id=user.id)
