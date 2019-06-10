# Celery tasks
from __future__ import absolute_import

import csv
import io
import redis
import time

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import get_connection, EmailMessage
from django.urls import reverse
from django.utils.translation import ugettext as _
from smtplib import SMTPException

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
        cache.set(task_id, temp_csv.getvalue(), timeout=settings.REDIS_LONG_EXPIRE)

    return {"current": users_n, "total": users_n}

@shared_task(name="teacher_tools.send_reminder_emails", bind=True)
def send_reminder_emails(self, course_slug, instance_slug, title, header, footer):
    course = Course.objects.get(slug=course_slug)
    instance = CourseInstance.objects.get(slug=instance_slug)

    reminder_cache = cache.get("{}_reminders".format(instance.slug))
    reminder_list = reminder_cache["reminders"]
    users_n = len(reminder_list)
    
    progress = reminder_cache["progress"]

    self.update_state(state="PROGRESS", meta={"current": 0, "total": users_n})

    connection = get_connection()
    mailfrom = "{}-reminders@{}".format(instance.slug, settings.ALLOWED_HOSTS[0])
    reply_to = instance.email

    for i, reminder in enumerate(reminder_list[progress - 1:], start=progress):
        body = header
        body += "\n\n--\n\n"
        body += reminder["missing_str"]
        body += "\n\n--\n\n"
        recipient = reminder["email"]
        
        mail = EmailMessage(title, body, mailfrom, [recipient], headers={"Reply-to": reply_to}, connection=connection)
        
        # try again once if sending fails
        # report a failure
        try:
            mail.send()
        except SMTPException:
            time.sleep(10)
            try:
                connection = get_connection()
                mail.send()
            except Exception:
                reminder_cache["progress"] = i
                cache.set("{}_reminders".format(instance.slug), reminder_cache)
                return {"current": i, "total": users_n, "aborted": _("Sending failed. Try again to resume.")}

        self.update_state(state="PROGRESS", meta={"current": i, "total": users_n})

    cache.delete("{}_reminders".format(instance.slug))

    return {"current": users_n, "total": users_n}

@shared_task(name="teacher_tools.order_moss_report", bind=True)
def order_moss_report(self, instance, exercise, language, excl_sub, exlc_fn, m, base_files):
    
    pass