from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def get_embed_frame_options(context, content, revision, category):
    options = []
    if category == "staff":
        options.append((
            _("Statistics"),
            "self",
            reverse("stats:single_exercise", kwargs={"exercise": content}),
        ))
    return options



