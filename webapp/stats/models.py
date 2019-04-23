import datetime

from django.db import models
from courses.models import ContentPage, CourseInstance, User


class StudentTaskStats(models.Model):
    
    student = models.ForeignKey(User, on_delete=models.CASCADE)
    task = models.ForeignKey(ContentPage, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(blank=True, null=True)
    instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    
    total_answers = models.PositiveIntegerField()
    tries_until_correct = models.PositiveIntegerField()
    correct_answers = models.PositiveIntegerField()
    before_deadline = models.PositiveIntegerField(null=True)
    after_deadline = models.PositiveIntegerField(null=True)
    same_answers = models.PositiveIntegerField(default=0)
    correct_before_dl = models.BooleanField(default=False)
    first_answer = models.DateTimeField(null=True)
    first_correct = models.DateTimeField(null=True)
    last_answer = models.DateTimeField(null=True)
    
    study_sessions = models.ManyToManyField("StudySession", blank=True)
    
    
class TaskSummary(models.Model):
    
    task = models.ForeignKey(ContentPage, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(blank=True, null=True)
    instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    
    # total_answers includes answers given after completing task
    total_answers = models.PositiveIntegerField()
    total_tries = models.PositiveIntegerField()
    total_users = models.PositiveIntegerField()
    correct_by_total = models.PositiveIntegerField()
    correct_by_before_dl = models.PositiveIntegerField()
    correct_by_after_dl = models.PositiveIntegerField()
    tries_avg = models.FloatField()
    tries_median = models.PositiveIntegerField()
    time_avg = models.DurationField()
    time_median = models.DurationField()

    def get_time_avg(self):
        value = self.time_avg
        rounded = value - datetime.timedelta(microseconds=value.microseconds)
        return rounded
    
    def get_time_median(self):
        value = self.time_median
        rounded = value - datetime.timedelta(microseconds=value.microseconds)
        return rounded
        
        
    
class StudySession(models.Model):
    
    start = models.DateTimeField()
    end = models.DateTimeField()
    
    tasks_answered = models.ManyToManyField("StudentTaskStats", blank=True)
    

    
        
    