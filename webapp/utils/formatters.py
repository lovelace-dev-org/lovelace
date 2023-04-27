"""
Contains formatting utils for making various strings that are used often.
"""


def display_name(user):
    """
    Returns a user's name as lastname firstname, provided that the user object
    has the last_name parameter set. First name is omitted if not set. If the
    user hasn't set their last name, their username will be returned instead.
    """

    if user.last_name:
        return user.last_name + " " + (user.first_name or "")
    return user.username
