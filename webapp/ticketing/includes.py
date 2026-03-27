from django.urls import reverse
from django.utils.translation import gettext_lazy as _

def get_user_menu_options(context):
    if not context.get("instance"):
        return []

    options = []
    kwargs = {"instance": context["instance"]}
    if context.get("enrolled"):
        options.append((
            _("Request Credits"),
            "self",
            reverse("ticketing:request_credits", kwargs=kwargs)
        ))

    if context.get("course_staff"):
        options.append((
            _("View Tickets"),
            "self",
            reverse("ticketing:view_tickets", kwargs=kwargs)
        ))

    return options
