from django.db import models
import courses.models as cm
from courses.widgets import AnswerWidgetRegistry
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

    def export(self, instance, export_target):
        super().export(instance, export_target)
        if self.base_file:
            self.base_file.export(instance, export_target)


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


class AcePlusLinkManager(models.Manager):

    def get_by_natural_key(self, widget_slug, instance_slug, parent_slug):
        return self.get(
            widget_slug=widget_slug,
            instance__slug=instance_slug,
            parent__slug=parent_slug,
        )


class AcePlusLink(models.Model, ExportImportMixin):

    class Meta:
        unique_together = ("widget_slug", "instance", "parent")

    objects = AcePlusLinkManager()

    widget_slug = models.CharField(max_length=255)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)
    parent = models.ForeignKey(cm.ContentPage, on_delete=models.CASCADE)

    def natural_key(self):
        return [self.widget_slug, self.instance.slug, self.parent.slug]

    def export(self, instance, export_target):
        widget = AnswerWidgetRegistry.get_widget("ace-plus", instance.course, self.widget_slug)
        widget.export(instance, export_target)


def export_models(instance, export_target):
    for link in AcePlusLink.objects.filter(instance=instance):
        link.export(instance, export_target)

def get_import_list():
    return [
        AceWidgetSettings,
        AcePlusWidgetSettings,
        AcePlusLink,
    ]

def update_context_links(page, instance, parsed_links, revision=None):
    new_links = parsed_links["aceplus"]
    old_links = list(
        AcePlusLink.objects.filter(parent=page, instance=instance).values_list(
            "widget_slug", flat=True
        )
    )
    removed_links = set(old_links).difference(new_links)
    added_links = set(new_links).difference(old_links)

    AcePlusLink.objects.filter(
        widget_slug__in=removed_links, instance=instance, parent=page
    ).delete()

    for link_slug in added_links:
        link_obj = AcePlusLink(
            widget_slug=link_slug,
            instance=instance,
            parent=page
        )
        link_obj.save()


