# Celery tasks
from __future__ import absolute_import

import csv
import io
import redis

from celery import shared_task
from django.conf import settings
from django.urls import reverse
from django.utils.translation import ugettext as _

from courses.models import Course, CourseInstance

from utils.content import get_course_instance_tasks
from teacher_tools.utils import compile_student_results

@shared_task(name="teacher_tools.generate_completion_csv", bind=True)
def generate_completion_csv(self, course_slug, instance_slug):
    course = Course.objects.get(slug=course_slug)
    instance = CourseInstance.objects.get(slug=instance_slug)
    
    users = instance.enrolled_users.get_queryset().order_by("last_name", "first_name", "username")
    users_n = users.count()
    tasks_by_page = get_course_instance_tasks(instance)

    self.update_state(state="PROGRESS", meta={"current": 0, "total": users_n})

    with io.StringIO() as temp_csv:
        writer = csv.writer(temp_csv)
        writer.writerow([
            _("username"), _("last name"), _("first name"), _("student id"),
            _("points"), _("missing"), _("email"), _("results url")
        ])

        for i, user in enumerate(users, start=1):
            results_by_page, total_points, total_missing, total_points_available = compile_student_results(user, instance, tasks_by_page)
            results_url = reverse("teacher_tools:student_completion", kwargs={
                "course": course,
                "instance": instance,
                "user": user
            })
            writer.writerow([
                user.username, user.last_name, user.first_name, user.userprofile.student_id,
                total_points, total_missing, user.email, results_url
            ])
            self.update_state(state="PROGRESS", meta={"current": i, "total": users_n})

        task_id = self.request.id
        r = redis.StrictRedis(**settings.REDIS_RESULT_CONFIG)
        r.set(task_id, temp_csv.getvalue(), ex=settings.REDIS_LONG_EXPIRE)

    return {"current": users_n, "total": users_n}

