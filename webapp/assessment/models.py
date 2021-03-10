from courses.models import CourseInstance, ContentPage
from django.db import models
from reversion.models import Version
from utils.archive import find_latest_version

class AssessmentToExerciseLink(models.Model):
    instance = models.ForeignKey("courses.CourseInstance", on_delete=models.CASCADE)
    exercise = models.ForeignKey("courses.ContentPage", on_delete=models.CASCADE)
    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(blank=True, null=True)
    
    def freeze(self, freeze_to):
        try:
            version = find_latest_version(self.sheet, freeze_to)
        except Version.DoesNotExist:
            self.delete()
            return
        
        self.revision = version.revision_id
        self.save()
            

# Create your models here.
class AssessmentSheet(models.Model):
    
    # Translatable fields
    title = models.CharField(max_length=255)
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE)
    
    
class AssessmentBullet(models.Model):
    
    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    point_value = models.FloatField(blank=True, null=False)
    ordinal_number = models.PositiveSmallIntegerField()
    
    # Translatable fields
    section = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    tooltip = models.TextField(blank=True, default="")