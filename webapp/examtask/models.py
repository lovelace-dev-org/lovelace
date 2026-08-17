from django.db import models
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _


import courses.models as cm

from utils.management import ExportImportMixin

# CONTENT MODELS
# |
# v

class ExamTask(cm.ContentPage):

    class Meta:
        verbose_name = "exam task"
        proxy = True

    default_answer_widget = "blank"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "EXAM_TASK"
        super().save(*args, **kwargs)

    def get_rendered_content(self, context):
        """
        Includes the multiexam content extra template into the rendered markup. This adds
        the 'Start exam' button and related information to the task.
        """

        content = cm.ContentPage._get_rendered_content(self, context)
        #t = loader.get_template("examtask/exam-content-extra.html")
        return content #+ [("extra", t.render(context), -1, 0)]

    def get_question(self, context):
        """
        Gets the question part of the task, no changes to the default.
        """

        return cm.ContentPage._get_question(self, context)

    def get_admin_change_url(self):
        """
        Returns admin change url for the model instance.
        """

        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:examtask_{adminized_type}_change", args=(self.id,))

    def get_staff_extra(self, context):
        """
        Adds a link to attempt management page to the task's staff tools.
        """

        options = cm.ContentPage.get_staff_extra(self, context)
        options.append((
            _("Edit task settings"),
            "examtask-settings",
            "side-panel",
            reverse("examtask:exam_task_settings", kwargs={
                "course": context["course"],
                "instance": context["instance"],
                "parent": context["parent"],
                "content": self,
            })
        ))
        options.append((
            _("Manage task attempts"),
            "examtask-attempts",
            "side-panel",
            reverse("examtask:exam_task_attempts", kwargs={
                "course": context["course"],
                "instance": context["instance"],
                "parent": context["parent"],
                "content": self,
            })
        ))
        return options

    def get_choices(self, revision=None):
        """
        This task type has a separate implementation for handling this behavior, so just returns
        None.
        """

        return

    def save_answer(self, user, ip, answer, files, instance, revision):
        # proxy the answer to the randomized task

        pass

    def check_answer(self, link, user, answer, files, answer_object):
        # proxy checking to the randomized task

        pass

    def get_user_answers(self, user, instance, ignore_drafts=True):
        # proxy to randomized task
        return cm.UserAnswer.objects.none()

    def export(self, instance, export_target):
        super(cm.ContentPage, self).export(instance, export_target)
        self.export_answer_widget(instance, export_target)
        settings = ExamTaskSettings.objects.get(task=self, instance=instance)
        settings.export(instance, export_target)



class ExamTaskSettingsManager(models.Manager):

    def get_by_natural_key(self, instance_slug, exam_slug):
        return self.get(
            instance__slug=instance_slug,
            exam__slug=exam_slug,
        )


class ExamTaskSettings(models.Model, ExportImportMixin):

    class Meta:
        unique_together = ("instance", "task")

    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)
    task = models.ForeignKey(ExamTask, on_delete=models.RESTRICT, related_name="task")
    task_pool = models.ManyToManyField(
        cm.ContentPage,
        through="ExamTaskToExerciseLink",
        through_fields=("settings", "exercise"),
        related_name="task_pool"
    )

    def export(self, instance, export_target):
        super().export(instance, export_target)
        for link in self.task_pool:
            link.export(instance, export_target)






class ExamTaskToExerciseManager(models.Manager):

    def get_by_natural_key(self, instance_slug, exam_slug, exercise_slug):
        return self.get(
            settings__instance__slug=instance_slug,
            settings__exam__slug=exam_slug,
            exercise__slug=exercise_slug,
        )


class ExamTaskToExerciseLink(models.Model, ExportImportMixin):

    class Meta:
        unique_together = ("settings", "exercise")

    objects = ExamTaskToExerciseManager()

    settings = models.ForeignKey(ExamTaskSettings, on_delete=models.RESTRICT)
    exercise = models.ForeignKey(cm.ContentPage, on_delete=models.RESTRICT)

    def natural_key(self):
        return [settings.exam.slug, settings.instance.slug, exercise.slug]



# ^
# |
# CONTENT MODELS
# ATTEMPT RELATED MODELS
# |
# v


class ExamTaskAttempt(models.Model):

    instance = models.ForeignKey(cm.CourseInstance, on_delete=models.CASCADE)
    title = models.CharField(max_length=256, blank=True)
    task = models.ForeignKey(ExamTask, on_delete=models.RESTRICT)
    start = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(cm.User, null=True, on_delete=models.CASCADE)



class ExamTaskChoice(models.Model):

    task = models.ForeignKey(ExamTaskToExerciseLink, on_delete=models.CASCADE)
    user = models.ForeignKey(cm.User, on_delete=models.CASCADE)
    attempt = models.ForeignKey(ExamTaskAttempt, on_delete=models.CASCADE)


cm.ContentPage.register_content_type(
    "EXAM_TASK", ExamTask, None, None
)
