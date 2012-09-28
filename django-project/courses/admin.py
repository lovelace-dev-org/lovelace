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

## Task types
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
class RadiobuttonTaskAnswerInline(admin.TabularInline):
    model = RadiobuttonTaskAnswer
    extra = 1

class RadiobuttonTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Page information',   {'fields': ['name', 'content', 'question', 'tags'],}),
        ('Task miscellaneous', {'fields': ['maxpoints', 'require_correct_embedded_tasks'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [RadiobuttonTaskAnswerInline]

class CheckboxTaskAnswerInline(admin.TabularInline):
    model = CheckboxTaskAnswer
    extra = 1

class CheckboxTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Page information',   {'fields': ['name', 'content', 'question', 'tags']}),
        ('Task miscellaneous', {'fields': ['maxpoints', 'require_correct_embedded_tasks'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [CheckboxTaskAnswerInline]

class TextfieldTaskAnswerInline(admin.StackedInline):
    model = TextfieldTaskAnswer
    extra = 1

class TextfieldTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Page information',   {'fields': ['name', 'content', 'question', 'tags']}),
        ('Task miscellaneous', {'fields': ['maxpoints', 'require_correct_embedded_tasks'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    inlines = [TextfieldTaskAnswerInline]

class FileTaskTestCommandAdmin(admin.TabularInline):
    model = FileTaskTestCommand
    extra = 1

    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(FileTaskTestCommandAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'command_line':
            formfield.widget = TextInput(attrs={'size':120})
        return formfield

class FileTaskTestExpectedOutputAdmin(admin.StackedInline):
    model = FileTaskTestExpectedOutput
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

class FileTaskTestExpectedErrorAdmin(admin.StackedInline):
    model = FileTaskTestExpectedError
    extra = 0
    fields = (('expected_answer', 'hint'), 'correct', 'regexp', 'videohint')

class FileTaskTestIncludeFileAdmin(admin.StackedInline):
    model = FileTaskTestIncludeFile
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

class FileTaskTestAdmin(admin.ModelAdmin):
    fieldsets = (
        ('General settings', {
            'fields': ('task', 'name', 'inputs')
        }),
        ('Advanced settings', {
            'classes': ('collapse',),
            'fields': ('timeout', 'signals', 'retval')
        }),
    )
    inlines = [FileTaskTestCommandAdmin, FileTaskTestExpectedOutputAdmin, FileTaskTestExpectedErrorAdmin, FileTaskTestIncludeFileAdmin]
    list_display = ("name", "task",)

#class FileTaskTestAdmin(admin.StackedInline):
#    inlines = [FileTaskTestCommandAdmin, FileTaskTestExpectedOutputAdmin, FileTaskTestExpectedErrorAdmin, FileTaskTestIncludeFileAdmin]

class FileTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        ('Page information',   {'fields': ['name', 'content', 'question', 'tags']}),
        ('Task miscellaneous', {'fields': ['maxpoints', 'require_correct_embedded_tasks'],
                                'classes': ['wide']}),
        ('Feedback settings',  {'fields': ['feedback_questions']}),
    ]
    #inlines = [FileTaskTestAdmin]

class LecturePageAdmin(admin.ModelAdmin):
    def formfield_for_dbfield(self, db_field, **kwargs):
        formfield = super(LecturePageAdmin, self).formfield_for_dbfield(db_field, **kwargs)
        if db_field.name == 'content':
            formfield.widget = Textarea(attrs={'rows':25, 'cols':120})
        elif db_field.name == 'tags':
            formfield.widget = Textarea(attrs={'rows':2})
        return formfield

admin.site.register(LecturePage, LecturePageAdmin)
admin.site.register(RadiobuttonTask, RadiobuttonTaskAdmin)
admin.site.register(CheckboxTask, CheckboxTaskAdmin)
admin.site.register(TextfieldTask, TextfieldTaskAdmin)
admin.site.register(FileTask, FileTaskAdmin)
admin.site.register(FileTaskTest, FileTaskTestAdmin)

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
admin.site.register(ContentFeedbackQuestion)

## Course related administration
class ContentGraphAdmin(admin.ModelAdmin):
    pass

admin.site.register(ContentGraph, ContentGraphAdmin)

class TrainingAdmin(admin.ModelAdmin):
 	fieldsets = [
        (None,                                               {'fields': ['name','frontpage','responsible']}),
        ('Training outline',                                 {'fields': ['contents']}),
        ('Settings for start date and end date of training', {'fields': ['start_date','end_date'], 'classes': ['collapse']}),
        ('Other staff for this training',                    {'fields': ['staff'], 'classes': ['collapse']}),
        ('Users enrolled in the training',                   {'fields': ['students'], 'classes': ['collapse']}),
    ]
	filter_horizontal = ['responsible','staff','students']
	#formfield_overrides = {models.ManyToManyField: {'widget':}}

admin.site.register(Training,TrainingAdmin)

