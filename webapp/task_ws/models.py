from django.db import models
import courses.models as cm
from utils.management import ExportImportMixin


# Create your models here.


class XtermWidgetSettings(models.Model, ExportImportMixin):

    class Meta:
        unique_together = ("key_slug", "instance")

    objects = cm.WidgetSettingsManager()
    key_slug = models.SlugField(max_length=255, blank=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)

    rows = models.PositiveSmallIntegerField(
        default=20,
        help_text="Number of rows in the terminal view (determines widget height)"
    )

    def natural_key(self):
        return self.instance.natural_key() + [self.key_slug]


class TurtleWidgetSettings(models.Model, ExportImportMixin):

    class Meta:
        unique_together = ("key_slug", "instance")

    objects = cm.WidgetSettingsManager()
    key_slug = models.SlugField(max_length=255, blank=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)

    def natural_key(self):
        return self.instance.natural_key() + [self.key_slug]

def export_models(instance, export_target):
    for model_inst in XtermWidgetSettings.objects.filter(instance=instance):
        model_inst.export(instance, export_target)
    for model_inst in TurtleWidgetSettings.objects.filter(instance=instance):
        model_inst.export(instance, export_target)

def get_import_list():
    return [
        TurtleWidgetSettings,
        XtermWidgetSettings,
    ]

