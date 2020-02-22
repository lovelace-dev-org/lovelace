from django.urls.converters import StringConverter
from courses.models import Course, CourseInstance, User

class Utf8SlugConverter(StringConverter):
    regex = "[-\w]+"

class RevisionConverter(StringConverter):
    regex = "\d+|head"

class InstanceConverter(Utf8SlugConverter):
    """
    Custom converter for instances. In addition to doing what model path 
    converter does, if the course slug is used in place of the instance slug
    will find the instance marked as primary instead. 
    
    This makes it possible to link to the primary instance from external
    sources instead of specifying an instance (that may become obsolete later).
    """


    def to_python(self, value):
        try:
            return CourseInstance.objects.get(slug=value)
        except CourseInstance.DoesNotExist:
            try:
                course = Course.objects.get(slug=value)
                return CourseInstance.objects.get(course=course, primary=True)
            except (CourseInstance.DoesNotExist, Course.DoesNotExist):
                raise ValueError

    def to_url(self, obj):
        if obj.primary:
            return obj.course.slug

        return obj.slug



    
    