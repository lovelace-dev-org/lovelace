from django.contrib import admin
from django.db import models

from reversion import revisions as reversion
from reversion.admin import VersionAdmin

from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
from utils.management import CourseContentAdmin
from courses.forms import ContentForm, ExerciseBackendForm

from answerless.models import AnswerlessTask

reversion.register(AnswerlessTask)

class AnswerlessAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):

    content_type = "ANSWERLESS_TASK"
    form = ContentForm

    fieldsets = [
        (
            "Page information",
            {
                "fields": ["name", "origin", "slug", "content", "question"],
            },
        ),
        (
            "Exercise miscellaneous",
            {
                "fields": [
                    "answer_widget",
                ],
                "classes": ["wide"],
            },
        ),
        ("Feedback settings", {"fields": ["feedback_questions"]}),
    ]

    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True

admin.site.register(AnswerlessTask, AnswerlessAdmin)
