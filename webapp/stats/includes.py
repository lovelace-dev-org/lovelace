from django.urls import reverse
from django.utils.translation import gettext_lazy as _

def get_content_menu_options(context, content, category):
    options = []
    if category == "staff":
        options.append((
            _("Statistics"),
            "stats",
            "self",
            reverse("stats:single_exercise", kwargs={"exercise": content}),
        ))
    return options


def get_embed_frame_options(context, content, link, category):
    options = []
    if category == "staff":
        options.append((
            _("Statistics"),
            "stats",
            "self",
            reverse("stats:single_exercise", kwargs={"exercise": content}),
        ))
    return options



