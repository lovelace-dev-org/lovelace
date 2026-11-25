from django.db import models
import courses.models as cm
from utils.management import ExportImportMixin, get_prefixed_slug


# Create your models here.


class XtermWidgetSettings(models.Model, ExportImportMixin):

    objects = cm.SlugManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course = models.ForeignKey(cm.Course, on_delete=models.CASCADE)

    rows = models.PositiveSmallIntegerField(
        default=20,
        help_text="Number of rows in the terminal view (determines widget height)"
    )

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(
            self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]


class TurtleWidgetSettings(models.Model, ExportImportMixin):

    objects = cm.SlugManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course = models.ForeignKey(cm.Course, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(
            self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]


class CompilerExplorerWidgetSettings(models.Model, ExportImportMixin):

    objects = cm.SlugManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course = models.ForeignKey(cm.Course, on_delete=models.CASCADE)

    rows = models.PositiveSmallIntegerField(
        default=20,
        help_text="Number of rows in the terminal view (determines widget height)"
    )

    compiler = models.CharField(
        max_length=255,
        default="g152",
        help_text="Compiler identifier for Compiler Explorer. Default is g152 (gcc 15.2). See https://godbolt.org/api/compilers for options."
    )

    default_stdin = models.TextField(
        max_length=1024,
        default="",
        help_text="Default input for the compiler stdin",
        blank=True
    )

    compiler_args = models.CharField(
        max_length=255,
        help_text="Default compiler arguments",
        blank=True
    )

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(
            self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]

class SQLWidgetSettings(models.Model, ExportImportMixin):

    objects = cm.SlugManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course = models.ForeignKey(cm.Course, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]


def export_models(instance, export_target):
    pass


def get_import_list():
    return [
        TurtleWidgetSettings,
        XtermWidgetSettings,
        CompilerExplorerWidgetSettings
        SQLWidgetSettings
    ]
