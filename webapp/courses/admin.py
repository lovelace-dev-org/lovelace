from courses.models import *

from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from django.core.urlresolvers import reverse

from django.db import models
from django.forms import TextInput, Textarea
from nested_inline.admin import NestedStackedInline, NestedTabularInline, NestedModelAdmin

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
class HintInline(NestedTabularInline):
    model = Hint
    fk_name = 'exercise'
    extra = 0
    queryset = NestedTabularInline.get_queryset

class MultipleChoiceExerciseAnswerInline(admin.TabularInline):
    model = MultipleChoiceExerciseAnswer
    extra = 1

class FileExerciseTestExpectedOutputInline(NestedStackedInline):
    model = FileExerciseTestExpectedOutput
    extra = 0
    fk_name = 'command'
    queryset = NestedStackedInline.get_queryset

class FileExerciseTestCommandInline(NestedStackedInline):
    model = FileExerciseTestCommand
    extra = 1
    fk_name = 'stage'
    queryset = NestedStackedInline.get_queryset
    fieldsets = (
        ('', {
            'fields': ('command_line', 'ordinal_number')
        }),
        ('Extra Options', {
            'classes': ('collapse',),
            'fields': ('significant_stdout', 'significant_stderr', 'timeout', 
                       'signal', 'input_text', 'return_value')
        }),
    )
    inlines = [FileExerciseTestExpectedOutputInline]

class FileExerciseTestStageInline(NestedStackedInline):
    model = FileExerciseTestStage
    fields = ('name', 'ordinal_number', 'depends_on',)
    extra = 1
    fk_name = 'test'
    inlines = [FileExerciseTestCommandInline]
    queryset = NestedStackedInline.get_queryset

class FileExerciseTestInline(NestedStackedInline):
    model = FileExerciseTest
    fields = ('exercise', 'name', 'required_files')
    extra = 1
    fk_name = 'exercise'
    inlines = [FileExerciseTestStageInline]
    queryset = NestedStackedInline.get_queryset
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "exercise":
            kwargs["queryset"] = FileUploadExercise.objects.order_by("name")
        return super(FileExerciseTestInline, self).formfield_for_foreignkey(db_field, request, **kwargs)

class FileExerciseTestIncludeFileInline(NestedStackedInline):
    model = FileExerciseTestIncludeFile
    extra = 0
    fk_name = 'exercise'
    queryset = NestedStackedInline.get_queryset
    fieldsets = (
        ('General information', {
            'fields': ('name', 'purpose', 'fileinfo')
        }),
        ('UNIX permissions', {
            'classes': ('collapse',),
            'fields': ('chown_settings', 'chgrp_settings', 'chmod_settings')
        }),
    )

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
    search_fields = ("name",)
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
    search_fields = ("name",)
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
    search_fields = ("name",)
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
    search_fields = ("name",)
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

# class FileExerciseTestAdmin(admin.ModelAdmin):
#     fieldsets = (
#         ('General settings', {
#             'fields': ('task', 'name', 'inputs')
#         }),
#         ('Advanced settings', {
#             'classes': ('collapse',),
#             'fields': ('timeout', 'signals', 'retval')
#         }),
#     )
#     inlines = []
#     search_fields = ("name",)
#     list_display = ("name", "exercise")
#     list_per_page = 500
    
#     def formfield_for_foreignkey(self, db_field, request, **kwargs):
#         if db_field.name == "exercise":
#             kwargs["queryset"] = FileUploadExercise.objects.order_by("name")
#         return super(FileExerciseTestAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

#class FileExerciseTestAdmin(admin.StackedInline):
#    inlines = [FileExerciseTestCommandAdmin, FileExerciseTestExpectedOutputAdmin, FileExerciseTestExpectedErrorAdmin, FileExerciseTestIncludeFileAdmin]


class FileExerciseAdmin(NestedModelAdmin):
    def get_queryset(self, request):
        return self.model.objects.filter(content_type="FILE_UPLOAD_EXERCISE")

    fieldsets = [
        ('Page information',   {'fields': ['name', 'slug', 'content', 'question', 'tags']}),
        ('Exercise miscellaneous', {'fields': ['default_points', 'manually_evaluated'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [HintInline, FileExerciseTestIncludeFileInline, FileExerciseTestInline]
    search_fields = ("name",)
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

    def view_on_site(self, obj):
        return reverse('courses:sandbox', kwargs={'content_slug': obj.slug})

    search_fields = ("name",)
    readonly_fields = ("slug",)
    list_display = ("name", "slug",)
    list_per_page = 500

# TODO: Use the view_on_site on all content models!

admin.site.register(Lecture, LectureAdmin)
admin.site.register(MultipleChoiceExercise, MultipleChoiceExerciseAdmin)
admin.site.register(CheckboxExercise, CheckboxExerciseAdmin)
admin.site.register(TextfieldExercise, TextfieldExerciseAdmin)
admin.site.register(CodeReplaceExercise, CodeReplaceExerciseAdmin)
admin.site.register(FileUploadExercise, FileExerciseAdmin)
#admin.site.register(FileExerciseTest, FileExerciseTestAdmin)
#admin.site.register(FileExerciseTest)
#admin.site.register(FileExerciseTestStage)
#admin.site.register(FileExerciseTestCommand)
#admin.site.register(FileExerciseTestExpectedOutput)
admin.site.register(FileExerciseTestIncludeFile)

## Page embeddable objects
class CalendarDateAdmin(admin.StackedInline):
    model = CalendarDate
    extra = 1

class CalendarAdmin(admin.ModelAdmin):
    inlines = [CalendarDateAdmin]
    search_fields = ("name",)

class FileAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.uploader = request.user
        obj.save()

    search_fields = ('name',)
    readonly_fields = ('uploader',)

class ImageAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.uploader = request.user
        obj.save()

    search_fields = ('name',)
    readonly_fields = ('uploader',)

class VideoLinkAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.added_by = request.user
        obj.save()

    search_fields = ('name',)
    readonly_fields = ('added_by',)

class TermAdmin(admin.ModelAdmin):    
    search_fields = ('name',)

admin.site.register(Calendar, CalendarAdmin)
admin.site.register(File, FileAdmin)
admin.site.register(Image, ImageAdmin)
admin.site.register(VideoLink, VideoLinkAdmin)
admin.site.register(Term, TermAdmin)

## Course related administration
class ContentGraphAdmin(admin.ModelAdmin):
    search_fields = ('content__slug',)

admin.site.register(ContentGraph, ContentGraphAdmin)

class CourseAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,             {'fields': ['name', 'slug', 'frontpage']}),
        ('Course outline', {'fields': ['description', 'code', 'credits', 'contents']}),
        #('Settings for start date and end date of the course', {'fields': ['start_date','end_date'], 'classes': ['collapse']}),
    ]
    #formfield_overrides = {models.ManyToManyField: {'widget':}}
    search_fields = ('name',)
    readonly_fields = ('slug',)

admin.site.register(Course, CourseAdmin)

class CourseInstanceAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,                {'fields': ['name', 'course']}),
        ('Schedule settings', {'fields': ['start_date', 'end_date', 'active']}),
    ]
    search_fields = ('name',)
    list_display = ('name', 'course')

admin.site.register(CourseInstance, CourseInstanceAdmin)
