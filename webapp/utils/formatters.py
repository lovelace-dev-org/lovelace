def display_name(user):
    if user.last_name:
        return user.last_name + " " + user.first_name
    else:
        return user.username