# Celery tasks
from __future__ import absolute_import

import datetime
import json
import redis
import statistics

from celery import shared_task
from django.conf import settings

from courses.models import ContentGraph, CourseInstance, UserAnswer
from .models import *

from utils.content import get_course_instance_tasks

from time import sleep

@shared_task(name="stats.generate-instance-user-stats")
def generate_instance_user_stats(instance_slug):

    instance = CourseInstance.objects.get(slug=instance_slug)

    StudentTaskStats.objects.filter(instance=instance).delete()

    task_pages = get_course_instance_tasks(instance)
    students = instance.enrolled_users.get_queryset()

    for user in students:
        print("Processing user", user.username)
        for page, task_links in task_pages:
            print("Processing page", page.name)
            deadline = ContentGraph.objects.filter(courseinstance=instance, content=page).first().deadline

            for link in task_links:
                task = link.embedded_page.get_type_object()
                print("Processing task", task.name)
                answers = UserAnswer.get_task_answers(task, user=user, instance=instance)
                total = answers.count()

                stats = StudentTaskStats(
                    student=user,
                    task=task,
                    instance=instance,
                    total_answers=total,
                )

                if total > 0:
                    stats.correct_answers = answers.filter(evaluation__correct=True).count()
                    stats.first_answer = answers.first().answer_date
                    stats.last_answer = answers.last().answer_date

                if stats.correct_answers > 0:
                    stats.first_correct = answers.filter(evaluation__correct=True).first().answer_date
                    stats.tries_until_correct = answers.filter(answer_date__lte=stats.first_correct).count()
                else:
                    stats.tries_until_correct = total

                if deadline:
                    stats.before_deadline = answers.filter(answer_date__lte=deadline).count()
                    stats.after_deadline = total - stats.before_deadline

                if deadline and stats.correct_answers > 0:
                    stats.correct_before_dl = stats.first_correct <= deadline

                stats.save()

    return datetime.datetime.now().strftime("%Y-%-m-%d %H:%M:%S")

@shared_task(name="stats.generate-instance-tasks-summary")
def generate_instance_tasks_summary(instance_slug):
    
    instance = CourseInstance.objects.get(slug=instance_slug)
    
    task_pages = get_course_instance_tasks(instance)
    
    TaskSummary.objects.filter(instance=instance).delete()
    
    for page, task_links in task_pages:
        for link in task_links:
            task = link.embedded_page.get_type_object()
            records = StudentTaskStats.objects.filter(instance=instance, task=task).exclude(total_answers=0)

            stats = TaskSummary(
                instance=instance,
                task=task,
                total_users=records.count()
            )

            total_answers = 0
            correct_by = 0
            correct_by_before_dl = 0
            try_counts = []
            times = []

            for record in records:
                total_answers += record.total_answers
                try_counts.append(record.tries_until_correct)
                if record.correct_answers:
                    correct_by += 1
                    if record.correct_before_dl:
                        correct_by_before_dl += 1
                    times.append(record.first_correct - record.first_answer)
                else:
                    times.append(record.last_answer - record.first_answer)

            try_counts.sort()
            times.sort()

            stats.total_answers = total_answers
            stats.correct_by_total = correct_by
            stats.correct_by_before_dl = correct_by_before_dl
            stats.correct_by_after_dl = correct_by - correct_by_before_dl
            stats.total_tries = sum(try_counts)
            stats.tries_avg = statistics.mean(try_counts)
            stats.tries_median = statistics.median(try_counts)
            stats.time_avg = sum(times, datetime.timedelta(0)) / len(times)
            stats.time_median = times[len(times) // 2]

            stats.save()
            
    return datetime.datetime.now().strftime("%Y-%-m-%d %H:%M:%S")

@shared_task(name="stats.finalize-instance-stats", bind=True)
def finalize_instance_stats(self, timestamp, instance_slug):
    
    r = redis.StrictRedis(**settings.REDIS_RESULT_CONFIG)
    r.set("{}_stat_meta".format(instance_slug), json.dumps({"task_id": self.request.id, "completed": timestamp}))
    
    
            
            
    
    
    
    

