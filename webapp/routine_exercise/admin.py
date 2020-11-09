from django.contrib.admin import StackedInline
from django.contrib import admin
from django.forms import Textarea

from reversion.admin import VersionAdmin
from reversion import revisions as reversion

from modeltranslation.admin import TranslationAdmin, TranslationStackedInline

from courses.forms import RepeatedTemplateExerciseBackendForm, ContentForm
from courses.widgets import ContentPreviewWidget

from routine_exercise.models import *
from routine_exercise.widgets import AdminRoutineBackendFileWidget

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
        models.FileField: {'widget': AdminRoutineBackendFileWidget}
    }
    classes = ["collapse"]


class RoutineExerciseBackendCommandInline(TranslationStackedInline):
    model = RoutineExerciseBackendCommand


class RoutineExerciseAdmin(CourseContentAccess, TranslationAdmin, VersionAdmin):

    change_form_template = "routine_exercise/admin-routine.html"
    
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
    
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        formfield = super().formfield_for_dbfield(db_field, request, **kwargs)
        if db_field.name in ('content'):
            formfield.widget = ContentPreviewWidget(attrs={'rows':25, 'cols':120})
        elif db_field.name == 'tags':
            formfield.widget = Textarea(attrs={'rows':2})
        return formfield
    

admin.site.register(RoutineExercise, RoutineExerciseAdmin)