from django.db import models
import courses.models as cm
from ace.utils import get_available_modes


class AceWidgetSettings(models.Model):

    class Meta:
        unique_together = ("key_slug", "instance")

    objects = cm.WidgetSettingsManager()

    key_slug = models.SlugField(max_length=255, blank=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)
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


class AcePlusWidgetSettings(models.Model):

    class Meta:
        unique_together = ("key_slug", "instance")

    objects = cm.WidgetSettingsManager()

    key_slug = models.SlugField(max_length=255, blank=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)

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

