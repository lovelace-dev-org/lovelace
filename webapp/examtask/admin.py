from django.contrib import admin

from reversion import revisions as reversion
from reversion.admin import VersionAdmin
from modeltranslation.admin import TranslationAdmin, TranslationStackedInline

from courses.forms import ContentForm
from utils.management import CourseContentAdmin

from .models import ExamTask

# Register your models here.

reversion.register(ExamTask)


class ExamTaskAdmin(CourseContentAdmin, TranslationAdmin, VersionAdmin):

    content_type = "EXAM TASK"
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
    inlines = [
    ]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = (
        "name",
        "slug",
    )
    list_per_page = 500
    save_on_top = True

admin.site.register(ExamTask, ExamTaskAdmin)

