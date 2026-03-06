from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def get_embed_frame_options(context, content, revision, category):
    options = []
    if not content.manually_evaluated:
        return options

    instance = context["instance"]
    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "content": content,
    }

    if category == "staff":
        options.append((
            _("View Submissions"),
            "self",
            reverse(
                "assessment:view_submissions", kwargs=content_kwargs
            )
        ))
        if revision is None:
            options.append((
                _("Edit Assessment"),
                "side-panel",
                reverse(
                    "assessment:manage_assessment", kwargs=content_kwargs
                )
            ))

    return options

def get_embed_frame_extra(context, content, revision, category):
    options = []
    if not content.manually_evaluated:
        return options

    instance = context["instance"]
    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "content": content,
    }
    if category == "student":
        options.append((
            _("Assessment Criteria"),
            "side-panel",
            reverse(
                "assessment:view_assessment", kwargs=content_kwargs
            )
        ))

    return options



