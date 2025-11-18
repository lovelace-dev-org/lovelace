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
        self.slug = get_prefixed_slug(self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]


class TurtleWidgetSettings(models.Model, ExportImportMixin):

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
    ]

