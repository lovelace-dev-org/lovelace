from courses.models import Course
from courses.models import Incarnation
from courses.models import ContentPage
from courses.models import File

from django.contrib import admin

admin.site.register(ContentPage)
admin.site.register(File)

class IncarnationInline(admin.StackedInline):
    model = Incarnation
    extra = 1

class CourseAdmin(admin.ModelAdmin):
    fields = ['name']

    inlines = [IncarnationInline]

admin.site.register(Course, CourseAdmin)

