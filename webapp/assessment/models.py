from courses.models import CourseInstance, ContentPage
from django.db import models
from reversion.models import Version
from utils.archive import find_latest_version, get_archived_instances

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
            
    def calculate_max_score(self):

        if self.revision is None:
            q = self.sheet.assessmentbullet_set.get_queryset().aggregate(
                max_score=models.Sum("point_value")
            )
            return q["max_score"]
        else:
            old_sheet = get_archived_instances(self.sheet, self.revision)
            bullets = old_sheet["assessmentbullet_set"]
            return sum(bullet.point_value for bullet in bullets)
        
            
# Create your models here.
class AssessmentSheet(models.Model):
    
    # Translatable fields
    title = models.CharField(max_length=255)
    course = models.ForeignKey("courses.Course", on_delete=models.CASCADE)
    
    
class AssessmentSection(models.Model):

    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    ordinal_number = models.PositiveSmallIntegerField()

    def __str__(self):
        return self.title

class AssessmentBullet(models.Model):
    
    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    point_value = models.FloatField(blank=False, null=False)
    ordinal_number = models.PositiveSmallIntegerField()
    
    # Translatable fields
    section = models.ForeignKey("AssessmentSection", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    tooltip = models.TextField(blank=True, default="")
