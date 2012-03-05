from courses.models import Course
from courses.models import Incarnation
from courses.models import ContentPage
from courses.models import File
from courses.models import TaskPage, RadiobuttonTask, CheckboxTask, TextfieldTask

from django.contrib import admin

admin.site.register(ContentPage)
admin.site.register(File)

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
    extra = 1

class CourseAdmin(admin.ModelAdmin):
    fields = ['name']

    inlines = [IncarnationInline]

admin.site.register(Course, CourseAdmin)
#admin.site.register(TaskPage, QuestionAdmin)
