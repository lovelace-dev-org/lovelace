import re
from django.urls import register_converter
from django.urls.converters import StringConverter, IntConverter
from courses.models import Course, CourseInstance


class Utf8SlugConverter(StringConverter):
    regex = r"[-\w]+"


class RevisionConverter(StringConverter):
    regex = r"\d+|head"


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
            except (CourseInstance.DoesNotExist, Course.DoesNotExist) as e:
                raise ValueError from e

    def to_url(self, value):
        if value.primary:
            return value.course.slug

        return value.slug


# Yoinked from model path converter and made django 5.1 compatible
# https://github.com/dhepper/django-model-path-converter
# |
# v

def camel_to_snake(s):
    camel_to_snake_regex = r'((?<=[a-z0-9])[A-Z]|(?!^)(?<!_)[A-Z](?=[a-z]))'
    return re.sub(camel_to_snake_regex, r'_\1', s).lower()


def snake_to_camel(s):
    snake_to_camel_regex = r"(?:^|_)(.)"
    return re.sub(snake_to_camel_regex, lambda m: m.group(1).upper(), s)


class ModelConverterMixin:

    def get_queryset(self):
        if self.queryset:
            return self.queryset.all()
        return self.model.objects.all()

    def to_python(self, value):
        try:
            return self.get_queryset().get(**{self.field: super().to_python(value)})
        except self.model.DoesNotExist:
            raise ValueError

    def to_url(self, obj):
        return super().to_url(getattr(obj, self.field))


def register_model_converter(model, name=None, field='pk', base=IntConverter, queryset=None):
    """
    Registers a custom path converter for a model.

    :param model: a Django model
    :param str name: name to register the converter as
    :param str field: name of the lookup field
    :param base: base path converter, either by name or as class
                 (optional, defaults to `django.urls.converter.IntConverter`)
    :param queryset: a custom querset to use (optional, defaults to `model.objects.all()`)
    """
    if name is None:
        name = camel_to_snake(model.__name__)
        converter_name = '{}Converter'.format(model.__name__)
    else:
        converter_name = '{}Converter'.format(snake_to_camel(name))

    if isinstance(base, str):
        base = get_converters()[base].__class__

    converter_class = type(
        converter_name,
        (ModelConverterMixin, base,),
        {'model': model, 'field': field, 'queryset': queryset}
    )

    register_converter(converter_class, name)
