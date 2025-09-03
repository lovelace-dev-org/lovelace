from django.db import models
import courses.models as cm
from ace.utils import get_available_modes
from utils.management import ExportImportMixin, get_prefixed_slug


class AceWidgetSettings(models.Model, ExportImportMixin):

    objects = cm.SlugManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course = models.ForeignKey(cm.Course, on_delete=models.CASCADE)
    font_size = models.PositiveSmallIntegerField(default=16)
    editor_height = models.PositiveSmallIntegerField(
        default=300,
        help_text="Height of the editor container in pixels"
    )
    language_mode = models.CharField(
        verbose_name="Editor syntax highlight language",
        max_length=32,
        choices=sorted(((name, name) for name in get_available_modes())),
    )
    extra_settings = models.JSONField(
        null=True,
        blank=True,
        help_text="Define any other Ace settings as JSON"
    )
    base_file = models.ForeignKey(cm.File, on_delete=models.SET_NULL, null=True)

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]


class AcePlusWidgetSettings(models.Model, ExportImportMixin):

    objects = cm.SlugManager()

    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    course = models.ForeignKey(cm.Course, on_delete=models.CASCADE)

    ace_settings = models.OneToOneField(
        AceWidgetSettings,
        on_delete=models.SET_NULL,
        null=True
    )
    preview_widget = models.CharField(
        verbose_name="Interactive preview widget.",
        max_length=32,
    )
    ws_address = models.CharField(
        verbose_name="Preview backend websocket address.",
        max_length=256
    )
    layout = models.CharField(
        verbose_name="Layout style",
        max_length=16,
        choices=(
            ("horizontal", "Horizontal"),
            ("vertical", "Vertical")
        ),
        default="horizontal"
    )

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.course, "name", translated=False)
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]


def export_models(instance, export_target):
    for model_inst in AceWidgetSettings.objects.filter(instance=instance):
        model_inst.export(instance, export_target)
    for model_inst in AcePlusWidgetSettings.objects.filter(instance=instance):
        model_inst.export(instance, export_target)

def get_import_list():
    return [
        AceWidgetSettings,
        AcePlusWidgetSettings,
    ]
