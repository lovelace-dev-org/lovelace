from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def get_base_static_includes(context):
    return [
        ("style", "assessment/assessment.css"),
        ("script", "assessment/assessment.js"),
    ]


def get_embed_frame_options(context, content, link, category):
    options = []
    instance = context["instance"]
    parent = context["content"]
    if not link.manually_evaluated:
        return options

    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "parent": parent,
        "content": content,
    }

    if category == "staff":
        options.append((
            _("View Submissions"),
            "submissions",
            "self",
            reverse(
                "assessment:view_submissions", kwargs=content_kwargs
            )
        ))
        if link.revision is None:
            options.append((
                _("Edit Assessment"),
                "edit-assessment",
                "side-panel",
                reverse(
                    "assessment:manage_assessment", kwargs=content_kwargs
                )
            ))

    return options

def get_embed_frame_extra(context, content, category):
    options = []
    instance = context["instance"]
    parent = context["content"]
    link = context["embed_link"]

    if not link.manually_evaluated:
        return options

    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "parent": parent,
        "content": content,
    }
    if category == "student":
        options.append((
            _("Assessment Criteria"),
            "assessment-criteria",
            "side-panel",
            reverse(
                "assessment:view_assessment_sheet", kwargs=content_kwargs
            )
        ))

    return options

def get_answer_actions(context, content, answer):
    instance = context["instance"]
    parent = context["exercise"]
    link = context["embed_link"]

    if not link.manually_evaluated:
        return []

    buttons = []
    answer_kwargs = {
        "course": instance.course,
        "instance": instance,
        "exercise": content,
        "user": context["student"],
        "answer": answer,
    }
    if answer.evaluation.feedback and answer.evaluation.completed:
        buttons.append((
            _("View assessment"),
            "report-button",
            "popup-panel",
            reverse(
                "assessment:view_assessment", kwargs=answer_kwargs
            ),
        ))

    if context["course_staff"]:
        buttons.append((
            _("Assess submission"),
            "inspect-button",
            "self",
            reverse(
                "assessment:submission_assessment", kwargs=answer_kwargs
            ),
        ))

    return buttons


