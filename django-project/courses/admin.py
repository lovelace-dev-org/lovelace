from courses.models import *

from django.contrib import admin

class RadiobuttonTaskAnswerInline(admin.TabularInline):
    model = RadiobuttonTaskAnswer
    extra = 1

class RadiobuttonTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]
    inlines = [RadiobuttonTaskAnswerInline]

class CheckboxTaskAnswerInline(admin.TabularInline):
    model = CheckboxTaskAnswer
    extra = 1

class CheckboxTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]
    inlines = [CheckboxTaskAnswerInline]

class TextfieldTaskAnswerInline(admin.StackedInline):
    model = TextfieldTaskAnswer
    extra = 1

class TextfieldTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]
    inlines = [TextfieldTaskAnswerInline]

class FileTaskTestCommandAdmin(admin.TabularInline):
    model = FileTaskTestCommand
    extra = 1

class FileTaskTestExpectedOutputAdmin(admin.StackedInline):
    model = FileTaskTestExpectedOutput
    extra = 0

class FileTaskTestExpectedErrorAdmin(admin.StackedInline):
    model = FileTaskTestExpectedError
    extra = 0

class FileTaskTestIncludeFileAdmin(admin.StackedInline):
    model = FileTaskTestIncludeFile
    extra = 0

class FileTaskTestAdmin(admin.ModelAdmin):
    inlines = [FileTaskTestCommandAdmin, FileTaskTestExpectedOutputAdmin, FileTaskTestExpectedErrorAdmin, FileTaskTestIncludeFileAdmin]

class FileTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None, {'fields': ['question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]

admin.site.register(LecturePage)
admin.site.register(RadiobuttonTask, RadiobuttonTaskAdmin)
admin.site.register(CheckboxTask, CheckboxTaskAdmin)
admin.site.register(TextfieldTask, TextfieldTaskAdmin)
admin.site.register(FileTask, FileTaskAdmin)
admin.site.register(FileTaskTest, FileTaskTestAdmin)

admin.site.register(File)
admin.site.register(Image)
admin.site.register(Video)
admin.site.register(Evaluation)

class ContentGraphAdmin(admin.ModelAdmin):
    pass

admin.site.register(ContentGraph, ContentGraphAdmin)

# http://jeffelmore.org/2010/11/11/automatic-downcasting-of-inherited-models-in-django/
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

#class IncarnationInline(admin.StackedInline):
#    model = Incarnation
#    extra = 0

#class CourseAdmin(admin.ModelAdmin):
#    fields = ['name']
#
#    inlines = [IncarnationInline]

class TrainingAdmin(admin.ModelAdmin):
 	fieldsets = [
        	(None,               {'fields': ['name','responsible','frontpage']}),
        	('Other staff for this training', {'fields': ['staff'],'classes': ['collapse']}),
        	('Settings for start date and end date of training', {'fields': ['start_date','end_date'],'classes': ['collapse']}),
        	('Users enrolled in the training', {'fields': ['students'],'classes': ['collapse']}),
        	('Training outline', {'fields': ['contents']}),
    		    ]
	filter_horizontal = ['responsible','staff','students']
	#formfield_overrides = {models.ManyToManyField: {'widget':}}

admin.site.register(Training,TrainingAdmin)
#admin.site.register(TaskPage, QuestionAdmin)


