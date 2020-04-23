from django.contrib.admin import StackedInline
from django.contrib import admin

from reversion.admin import VersionAdmin
from reversion import revisions as reversion

from modeltranslation.admin import TranslationAdmin, TranslationStackedInline

from courses.forms import RepeatedTemplateExerciseBackendForm, ContentForm
from courses.widgets import AdminTemplateBackendFileWidget

from routine_exercise.models import *

from utils.management import CourseContentAccess

reversion.register(RoutineExerciseTemplate)
reversion.register(RoutineExerciseBackendFile)
reversion.register(RoutineExerciseBackendCommand)


class RoutineExerciseTemplateInline(TranslationStackedInline):
    model = RoutineExerciseTemplate
    extra = 1
    classes = ["collapse"]


class RoutineExerciseBackendFileInline(StackedInline):
    model = RoutineExerciseBackendFile
    extra = 1
    form = RepeatedTemplateExerciseBackendForm
    formfield_overrides = {
        models.FileField: {'widget': AdminTemplateBackendFileWidget}
    }
    classes = ["collapse"]


class RoutineExerciseBackendCommandInline(TranslationStackedInline):
    model = RoutineExerciseBackendCommand


class RoutineExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):

    content_type = "ROUTINE_EXERCISE"
    form = ContentForm
    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'evaluation_group'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [
        RoutineExerciseTemplateInline,
        RoutineExerciseBackendFileInline,
        RoutineExerciseBackendCommandInline,
    ]
    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500
    save_on_top = True

admin.site.register(RoutineExercise, RoutineExerciseAdmin)