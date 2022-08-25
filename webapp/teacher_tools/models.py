import datetime

from django.conf import settings
from django.db import models
from django.dispatch import receiver
from django.contrib.postgres.fields import ArrayField
from django.utils.translation import gettext as _

from courses.models import Course, CourseInstance, User, FileUploadExercise
from utils.files import get_moss_basefile_path

import courses.models as cm

# Create your models here.

class ReminderTemplate(models.Model):
    
    instance = models.OneToOneField(CourseInstance, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, default="")
    header = models.TextField(blank=True, default="")
    footer = models.TextField(blank=True, default="")


class MossSettings(models.Model):

    exercise = models.ForeignKey(FileUploadExercise, on_delete=models.CASCADE, blank=True, null=True)
    matches = models.IntegerField(verbose_name=_("Number of matches to show"))
    language = models.CharField(
        max_length=32,
        choices=((lang, lang) for lang in settings.MOSSNET_LANGUAGES),
        verbose_name=_("Programming language")
    )
    file_extensions = ArrayField(
        base_field=models.CharField(max_length=32, blank=True),
        default=list,
        blank=True
    )
    exclude_filenames = ArrayField(
        base_field=models.CharField(max_length=32, blank=True),
        default=list,
        blank=True
    )
    exclude_subfolders = ArrayField(
        base_field=models.CharField(max_length=32, blank=True),
        default=list,
        blank=True
    )


class MossBaseFile(models.Model):

    fileinfo = models.FileField(max_length=255, upload_to=get_moss_basefile_path, storage=cm.upload_storage) 
    moss_settings = models.ForeignKey(MossSettings, null=True, blank=True, on_delete=models.CASCADE)
    exercise = models.ForeignKey(FileUploadExercise, on_delete=models.CASCADE)

@receiver(models.signals.post_delete, sender=MossBaseFile)
def delete_from_disk(sender, instance, **kwargs):
    instance.fileinfo.delete(False)