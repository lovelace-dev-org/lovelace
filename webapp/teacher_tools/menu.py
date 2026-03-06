from django.urls import reverse
from django.utils.translation import gettext_lazy as _


def get_embed_frame_options(context, content, revision, category):
    options = []
    instance = context["instance"]
    content_kwargs = {
        "course": instance.course,
        "instance": instance,
        "content": content,
    }

    if category == "staff":
        if content.content_type == "FILE_UPLOAD_EXERCISE":
            options.append((
                _("Download answers"),
                "self",
                reverse(
                    "teacher_tools:download_answers",
                    kwargs=content_kwargs,
                ),
            ))

        options.append((
            _("Answer summary"),
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
                "side-panel",
                reverse(
                    "teacher_tools:reset_completion",
                    kwargs=content_kwargs,
                ),
            ))
    return options
