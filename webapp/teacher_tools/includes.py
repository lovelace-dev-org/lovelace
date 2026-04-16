from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def get_user_menu_options(context):
    options = []
    instance = context.get("instance")
    if not instance:
        return []
    if not context.get("course_staff"):
        return []


    kwargs = {
        "course": instance.course,
        "instance": instance,
    }

    options.append((
        _("Manage enrollments"),
        "self",
        reverse("teacher_tools:manage_enrollments", kwargs=kwargs)
    ))
    options.append((
        _("Course completion"),
        "self",
        reverse("teacher_tools:completion", kwargs=kwargs)
    ))
    options.append((
        _("Search records"),
        "self",
        reverse("teacher_tools:search_records", kwargs=kwargs)
    ))
    options.append((
        _("Deadline exemptions"),
        "self",
        reverse("teacher_tools:exemptions", kwargs=kwargs)
    ))

    return options


def get_embed_frame_options(context, content, link, category):
    options = []
    instance = context["instance"]
    parent = context["content"]
    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "content": content,
        "parent": parent
    }

    if category == "staff":
        if content.content_type == "FILE_UPLOAD_EXERCISE":
            options.append((
                _("Download answers"),
                "download-answers",
                "self",
                reverse(
                    "teacher_tools:download_answers",
                    kwargs=content_kwargs,
                ),
            ))

        options.append((
            _("Answer summary"),
            "answer-summary",
            "self",
            reverse(
                "teacher_tools:answer_summary",
                    kwargs=content_kwargs,
            ),
        ))

        if content.content_type in [
            "TEXTFIELD_EXERCISE",
            "CHECKBOX_EXERCISE",
            "MULTIPLE_CHOICE_EXERCISE",
            "MULTIPLE_QUESTION_EXAM",
        ]:
            options.append((
                _("Batch grading"),
                "batch-grading",
                "side-panel",
                reverse(
                    "teacher_tools:batch_grade",
                    kwargs=content_kwargs,
                ),
            ))

        # Currently not in use
        if False:
            options.append((
                _("Reset completion"),
                "reset",
                "side-panel",
                reverse(
                    "teacher_tools:reset_completion",
                    kwargs=content_kwargs,
                ),
            ))
    return options
