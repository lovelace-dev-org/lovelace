from courses.models import Course
from courses.models import Incarnation
from django.contrib import admin

class IncarnationInline(admin.StackedInline):
    model = Incarnation
    extra = 1

class CourseAdmin(admin.ModelAdmin):
    fields = ['name']

    inlines = [IncarnationInline]

admin.site.register(Course, CourseAdmin)

