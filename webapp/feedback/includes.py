from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

def get_base_static_includes(context):
    return [
        ("style", "feedback/style.css"),
        ("script", "feedback/script.js"),
    ]

def get_content_page_additions(context, content, content_level):
    template = loader.get_template("feedback/feedbacks.html")
    c = {
        "feedback_questions": content.get_feedback_questions(),
        "user": context["user"],
        "content": content,
        "instance": context["instance"],
        "embedded": content_level == "embed",
        "csrf_token": context["csrf_token"],
    }
    return template.render(c)


def get_content_menu_options(context, content, category):
    options = []
    instance = context["instance"]
    if category == "staff":
        options.append((
            _("Feedback"),
            "feedback",
            "self",
            reverse(
                "feedback:statistics",
                kwargs={"instance": instance, "content": content},
            ),
        ))
    return options

def get_embed_frame_options(context, content, link, category):
    options = []
    instance = context["instance"]
    if category == "staff":
        options.append((
            _("Feedback"),
            "feedback",
            "self",
            reverse(
                "feedback:statistics",
                kwargs={"instance": instance, "content": content},
            ),
        ))

    return options
