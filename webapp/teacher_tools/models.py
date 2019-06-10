import datetime

from django.db import models
from django.contrib.postgres.fields import ArrayField
from courses.models import Course, CourseInstance, User, FileUploadExercise

import courses.models as cm

# Create your models here.

class ReminderTemplate(models.Model):
    
    instance = models.OneToOneField(CourseInstance, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, blank=True, default="")
    header = models.TextField(blank=True, default="")
    footer = models.TextField(blank=True, default="")
    
    
#class MossSettings(models.Model):
    
    #instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    #exercise = models.ForeignKey(FileUploadExercise, on_delete=models.CASCADE, blank=True, null=True)
    #language = models.CharField(max_length=32)
    #file_extensions = ArrayField(
        #base_field=models.CharField(max_length=32, blank=True),
        #default=list,
        #blank=True
    #)
    #exclude_filenames = ArrayField(
        #base_field=models.CharField(max_length=32, blank=True),
        #default=list,
        #blank=True
    #)
    #exclude_subfolders = ArrayField(
        #base_field=models.CharField(max_length=32, blank=True),
        #default=list,
        #blank=True
    #)
    #include_instances = models.ManyToManyField(CourseInstance, related_name="included_in")

    


#class MossBaseFile(models.Model):
    
    #fileinfo = models.FileField(max_length=255, upload_to=cm.get_instancefile_path, storage=cm.upload_storage) 
    #moss_settings = models.ForeignKey(MossSettings, on_delete=models.CASCADE)
    
    
    

    