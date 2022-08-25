# Celery tasks
from __future__ import absolute_import

import csv
import io
import os
import redis
import subprocess
import tempfile
import time

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.core.mail import get_connection, EmailMessage
from django.urls import reverse
from django.utils.translation import gettext as _
from smtplib import SMTPException

from courses.models import Course, CourseInstance, UserFileUploadExerciseAnswer
from utils.content import get_course_instance_tasks
from teacher_tools.models import MossBaseFile
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

    for i, reminder in enumerate(reminder_list[progress:], start=progress):
        body = header
        body += "\n\n--\n\n"
        body += reminder["missing_str"]
        body += "\n\n--\n\n"
        body += footer
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
                cache.set("{}_reminders".format(instance.slug), reminder_cache, timeout=settings.REDIS_LONG_EXPIRE)
                return {"current": i, "total": users_n, "aborted": _("Sending failed. Try again to resume.")}

        self.update_state(state="PROGRESS", meta={"current": i + 1, "total": users_n})

    cache.delete("{}_reminders".format(instance.slug))

    return {"current": users_n, "total": users_n}

def crawl(folder):
    content = os.listdir(folder)
    if content and all(fn.isdigit() for fn in content):
        content.sort()
        if newest_only:
            newest = content[-1]
            crawl(os.path.join(folder, newest))
        else:
            for fn in content:
                crawl(os.path.join(folder, fn))
    else:
        for fn in content:
            path = os.path.join(folder, fn)
            
            # this branch identifies files to submit
            if os.path.splitext(fn)[-1] in extensions:
                if not fn in exclude_files:
                    files_to_submit.append("\"" + path + "\"")
            else:
                if os.path.isdir(path):
                    if not any(fn.startswith(e) for e in exclude_subfolders):
                        crawl(path)

@shared_task(name="teacher_tools.order_moss_report", bind=True)
def order_moss_report(self, course_slug, instance_slug, exercise_slug, submit_form):

    newest_only = submit_form.get("versions") == "newest"
    extensions = submit_form["file_extensions"]
    exclude_files = submit_form.get("exclude_filenames", [])
    exclude_subfolders = submit_form.get("exclude_subfolders", [])

    files_to_submit = []

    def crawl(folder):
        content = os.listdir(folder)
        if content and all(fn.isdigit() for fn in content):
            content.sort()
            if newest_only:
                newest = content[-1]
                crawl(os.path.join(folder, newest))
            else:
                for fn in content:
                    crawl(os.path.join(folder, fn))
        else:
            for fn in content:
                path = os.path.join(folder, fn)

                # this branch identifies files to submit
                if os.path.splitext(fn)[-1] in extensions:
                    if not fn in exclude_files:
                        files_to_submit.append(path)
                else:
                    if os.path.isdir(path):
                        if not any(fn.startswith(e) for e in exclude_subfolders):
                            crawl(path)

    instances = [instance_slug]
    instances.extend(submit_form.get("include_instances", []))
    answerers_by_instance = []
    users_n = 0
    for islug in instances:
        answerers = UserFileUploadExerciseAnswer.objects.filter(
            exercise__slug=exercise_slug,
            instance__slug=islug
        ).distinct("user").values_list("user__username", flat=True)
        answerers_by_instance.append((islug, answerers))
        users_n += len(answerers)

    for islug, answerers in answerers_by_instance:
        for i, student in enumerate(answerers):
            self.update_state(state="PROGRESS", meta={"phase": "CHOOSE_FILES", "current": i + 1, "total": users_n})
            answers_path = os.path.join(
                settings.PRIVATE_STORAGE_FS_PATH,
                "returnables",
                islug,
                student,
                exercise_slug
            )
            crawl(answers_path)

    base_files = MossBaseFile.objects.filter(exercise__slug=exercise_slug)
    base_includes = []
    for bf in base_files:
        base_includes.append("-b")
        base_includes.append(os.path.join(settings.PRIVATE_STORAGE_FS_PATH, str(bf.fileinfo)))

    command = [
        settings.MOSSNET_SUBMIT_PATH,
        "-l", submit_form["language"],
        "-d",
        "-m", str(submit_form["matches"])
    ]
    command.extend(base_includes)
    command.extend(files_to_submit)

    print(command)

    #for base_file in MossBaseFile.objects.filter(moss_settings__exercise__slug=exercise_slug):
        #command += " -b {path}".format(
            #path=fs_path = os.path.join(settings.MEDIA_ROOT, base_file.fileinfo.name)

    stdin = tempfile.TemporaryFile()
    stdout = tempfile.TemporaryFile()
    stderr = tempfile.TemporaryFile()
    
    proc = subprocess.Popen(
        args=command, bufsize=-1, executable=None,
        stdin=stdin, stdout=stdout, stderr=stderr, # Standard fds
        close_fds=True,                            # Don't inherit fds
        shell=False,                               # Don't run in shell
        universal_newlines=False                   # Binary stdout
    )

    self.update_state(state="PROGRESS", meta={"phase": "MOSS_SUBMIT", "current": i + 1, "total": users_n})

    proc.wait(timeout=300)
    
    MossBaseFile.objects.filter(exercise__slug=exercise_slug, moss_settings=None).delete()
    
    stderr.seek(0)
    err = stderr.read().decode("utf-8")
    
    if err:
        return {"result": "error", "reason": err}
    
    stdout.seek(0)
    out = stdout.read().decode("utf-8")
    url = out.rstrip().split("\n")[-1]

    cache.set("{}_moss_result".format(exercise_slug), url, timeout=settings.REDIS_LONG_EXPIRE)

    return {"result": "success", "url": url}