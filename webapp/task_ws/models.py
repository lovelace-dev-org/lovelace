from django.db import models
import courses.models as cm

# Create your models here.


class XtermWidgetSettings(models.Model):

    class Meta:
        unique_together = ("key_slug", "instance")

    objects = cm.WidgetSettingsManager()
    key_slug = models.SlugField(max_length=255, blank=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)

    rows = models.PositiveSmallIntegerField(
        default=20,
        help_text="Number of rows in the terminal view (determines widget height)"
    )


class TurtleWidgetSettings(models.Model):

    class Meta:
        unique_together = ("key_slug", "instance")

    objects = cm.WidgetSettingsManager()
    key_slug = models.SlugField(max_length=255, blank=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)
