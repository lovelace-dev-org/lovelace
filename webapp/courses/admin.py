from courses.models import *

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from django.db import models
from django.forms import TextInput, Textarea

## User profiles
# http://stackoverflow.com/questions/4565814/django-user-userprofile-and-admin
admin.site.unregister(User)

class UserProfileInline(admin.StackedInline):
    model = UserProfile

class UserProfileAdmin(UserAdmin):
    inlines = [UserProfileInline,]

admin.site.register(User, UserProfileAdmin)

## Feedback for user answers
admin.site.register(Evaluation)

## Exercise types
# TODO: Create an abstract way to admin the different task types
#class AbstractQuestionAdmin(admin.ModelAdmin):
#    def save_model(self, request, obj, form, change):
#        obj.save()
#        if not change:
#            obj.users.add(request, user)
#
##    def queryset(self, request):
#        qs = super(AbstractQuestionAdmin, self).queryset(request)
#        if request.user.is_superuser:
#            return qs.select_subclasses()
#        return qs.select_subclasses().filter(users=request.user)

# TODO: How to link ContentFeedbackQuestion objects nicely?
class HintInline(admin.TabularInline):
    model = Hint
    extra = 0

class MultipleChoiceExerciseAnswerInline(admin.TabularInline):
    model = MultipleChoiceExerciseAnswer
    extra = 1

class MultipleChoiceExerciseAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="MULTIPLE_CHOICE_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags'],}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [MultipleChoiceExerciseAnswerInline, HintInline]
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

class CheckboxExerciseAnswerInline(admin.TabularInline):
    model = CheckboxExerciseAnswer
    extra = 1

class CheckboxExerciseAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="CHECKBOX_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CheckboxExerciseAnswerInline, HintInline]
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

class TextfieldExerciseAnswerInline(admin.StackedInline):
    model = TextfieldExerciseAnswer
    extra = 1

class TextfieldExerciseAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="TEXTFIELD_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [TextfieldExerciseAnswerInline, HintInline]
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

class CodeReplaceExerciseAnswerInline(admin.StackedInline):
    model = CodeReplaceExerciseAnswer
    extra = 1

class CodeReplaceExerciseAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="CODE_REPLACE_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CodeReplaceExerciseAnswerInline, HintInline]
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

class FileExerciseTestCommandAdmin(admin.TabularInline):
    model = FileExerciseTestCommand
    extra = 1

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(FileExerciseTestCommandAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'command_line':
            formfield.widget = TextInput(attrs={'size':120})
        return formfield

class FileExerciseTestExpectedStdoutAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStdout
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

class FileExerciseTestExpectedStderrAdmin(admin.StackedInline):
    model = FileExerciseTestExpectedStderr
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

class FileExerciseTestIncludeFileAdmin(admin.StackedInline):
    model = FileExerciseTestIncludeFile
    extra = 0
    fieldsets = (
        ('General information', {
            'fields': ('name', 'purpose', 'fileinfo')
        }),
        ('UNIX permissions', {
            'classes': ('collapse',),
            'fields': ('chown_settings', 'chgrp_settings', 'chmod_settings')
        }),
    )

class FileExerciseTestAdmin(admin.ModelAdmin):
    fieldsets = (
        ('General settings', {
            'fields': ('task', 'name', 'inputs')
        }),
        ('Advanced settings', {
            'classes': ('collapse',),
            'fields': ('timeout', 'signals', 'retval')
        }),
    )
    inlines = []
    list_display = ("name", "exercise",)
    list_per_page = 500
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "exercise":
            kwargs["queryset"] = FileUploadExercise.objects.order_by("name")
        return super(FileExerciseTestAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

#class FileExerciseTestAdmin(admin.StackedInline):
#    inlines = [FileExerciseTestCommandAdmin, FileExerciseTestExpectedOutputAdmin, FileExerciseTestExpectedErrorAdmin, FileExerciseTestIncludeFileAdmin]

class FileExerciseAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="FILE_UPLOAD_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [HintInline]
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

class LectureAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="LECTURE")

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(LectureAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'content':
            formfield.widget = Textarea(attrs={'rows':25, 'cols':120})
        elif db_field.name == 'tags':
            formfield.widget = Textarea(attrs={'rows':2})
        return formfield
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

admin.site.register(Lecture, LectureAdmin)
admin.site.register(MultipleChoiceExercise, MultipleChoiceExerciseAdmin)
admin.site.register(CheckboxExercise, CheckboxExerciseAdmin)
admin.site.register(TextfieldExercise, TextfieldExerciseAdmin)
admin.site.register(CodeReplaceExercise, CodeReplaceExerciseAdmin)
admin.site.register(FileUploadExercise, FileExerciseAdmin)
admin.site.register(FileExerciseTest, FileExerciseTestAdmin)

## Page embeddable objects
class CalendarDateAdmin(admin.StackedInline):
    model = CalendarDate
    extra = 1

class CalendarAdmin(admin.ModelAdmin):
    inlines = [CalendarDateAdmin]

admin.site.register(Calendar, CalendarAdmin)
admin.site.register(File)
admin.site.register(Image)
admin.site.register(Video)

## Course related administration
class ContentGraphAdmin(admin.ModelAdmin):
    pass

admin.site.register(ContentGraph, ContentGraphAdmin)

class CourseAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,             {'fields': ['name', 'slug', 'frontpage']}),
        ('Course outline', {'fields': ['description', 'code', 'credits', 'contents']}),
        #('Settings for start date and end date of the course', {'fields': ['start_date','end_date'], 'classes': ['collapse']}),
    ]
    #formfield_overrides = {models.ManyToManyField: {'widget':}}
    readonly_fields = ('slug',)

admin.site.register(Course, CourseAdmin)

