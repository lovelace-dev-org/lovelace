from django.db import models
import courses.models as cm

# Create your models here.


class XtermWidgetSettings(models.Model):

    objects = cm.WidgetSettingsManager()
    content = models.ForeignKey(cm.ContentPage, on_delete=models.CASCADE, null=True)
    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)

    rows = models.PositiveSmallIntegerField(
        default=20,
        help_text="Number of rows in the terminal view (determines widget height)"
    )






