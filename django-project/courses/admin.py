from courses.models import Course
from courses.models import Incarnation
from courses.models import ContentPage
from courses.models import File
from courses.models import LecturePage, TaskPage, RadiobuttonTask, CheckboxTask, TextfieldTask
from courses.models import RadiobuttonTaskAnswer, CheckboxTaskAnswer, TextfieldTaskAnswer
from courses.models import ContentGraph, ContentGraphNode

from django.contrib import admin

class RadiobuttonTaskAnswerInline(admin.TabularInline):
    model = RadiobuttonTaskAnswer
    extra = 1

class RadiobuttonTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['course', 'question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]
    inlines = [RadiobuttonTaskAnswerInline]

class CheckboxTaskAnswerInline(admin.TabularInline):
    model = CheckboxTaskAnswer
    extra = 1

class CheckboxTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['course', 'question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]
    inlines = [CheckboxTaskAnswerInline]

class TextfieldTaskAnswerInline(admin.StackedInline):
    model = TextfieldTaskAnswer
    extra = 1

class TextfieldTaskAdmin(admin.ModelAdmin):
    fieldsets = [
        (None,               {'fields': ['course', 'question']}),
        ('Page information', {'fields': ['name', 'content']}),
    ]
    inlines = [TextfieldTaskAnswerInline]


admin.site.register(LecturePage)
admin.site.register(RadiobuttonTask, RadiobuttonTaskAdmin)
admin.site.register(CheckboxTask, CheckboxTaskAdmin)
admin.site.register(TextfieldTask, TextfieldTaskAdmin)
admin.site.register(File)

class ContentGraphNodeInline(admin.TabularInline):
    model = ContentGraphNode

class ContentGraphAdmin(admin.ModelAdmin):
    inlines = [ContentGraphNodeInline]

class ContentGraphNodeAdmin(admin.ModelAdmin):
    inlines = [
        ContentGraphNodeInline,
    ]

admin.site.register(ContentGraphNode, ContentGraphNodeAdmin)
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

class IncarnationInline(admin.StackedInline):
    model = Incarnation
    extra = 0

class CourseAdmin(admin.ModelAdmin):
    fields = ['name']

    inlines = [IncarnationInline]

admin.site.register(Course, CourseAdmin)
#admin.site.register(TaskPage, QuestionAdmin)
