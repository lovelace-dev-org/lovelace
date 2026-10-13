from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .utils import has_faq

def get_base_static_includes(context):
    return [
        ("style", "faq/faq.css"),
        ("script", "faq/faq.js"),
    ]


def get_embed_frame_extra(context, content, category):
    options = []

    instance = context["instance"]
    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "exercise": content,
    }
    if category == "student":
        options.append((
            _("Frequently Asked Questions"),
            "faq",
            "side-panel",
            reverse(
                "faq:faq_panel", kwargs=content_kwargs
            )
        ))

    return options

def get_exercise_trigger_callbacks(instance, content, data):
    if has_faq(instance, content, data["triggers"]):
        return ["faq"]
    return []
