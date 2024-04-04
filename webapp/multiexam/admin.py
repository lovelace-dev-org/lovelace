from django.contrib import admin

from reversion import revisions as reversion
from reversion.admin import VersionAdmin

from modeltranslation.admin import TranslationAdmin, TranslationStackedInline
from utils.management import CourseContentAdmin
from courses.forms import ContentForm
from multiexam.forms import QuestionPoolForm
from multiexam.models import (
    MultipleQuestionExam,
    ExamQuestionPool,
)

# Register your models here.

reversion.register(MultipleQuestionExam)
reversion.register(ExamQuestionPool)


class QuestionPoolInline(TranslationStackedInline):
    model = ExamQuestionPool
    form = QuestionPoolForm



class MultiExamAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):

    content_type = "MULTIPLE_QUESTION_EXAM"
    form = ContentForm

    fieldsets = [
        (
            "Page information",
            {
                "fields": ["name", "origin", "slug", "content", "question", "tags"],
            },
        ),
        (
            "Exercise miscellaneous",
            {
                "fields": [
                    "default_points",
                    "answer_limit",
                    "manually_evaluated",
                    "delayed_evaluation",
                    "group_submission",
                    "evaluation_group",
                ],
                "classes": ["wide"],
            },
        ),
        ("Feedback settings", {"fields": ["feedback_questions"]}),
    ]
    inlines = [
        QuestionPoolInline
    ]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True

admin.site.register(MultipleQuestionExam, MultiExamAdmin)

