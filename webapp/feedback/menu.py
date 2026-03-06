from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def get_embed_frame_options(context, content, revision, category):
    options = []
    instance = context["instance"]
    if category == "staff":
        options.append((
            _("Feedback"),
            "self",
            reverse(
                "feedback:statistics",
                kwargs={"instance": instance, "content": content},
            ),
        ))

    return options
