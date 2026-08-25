import datetime
import random
from django.db import models
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _


import courses.models as cm

from utils.management import ExportImportMixin

class NoAttemptException(Exception):
    pass

# CONTENT MODELS
# |
# v

def get_attempt(task, instance, user):
    all_attempts = ExamTaskAttempt.objects.filter(task=task, instance=instance)
    if not all_attempts:
        raise NoAttemptException

    if personal_attempt := all_attempts.filter(user=user).first():
        return personal_attempt
    elif generic_attempt := all_attempts.filter(user=None).first():
        return generic_attempt

    raise NoAttemptException


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
        return content

    def get_question(self, context):
        """
        Gets the question part of the task, no changes to the default.
        """

        return cm.ContentPage._get_question(self, context)

    def dynamic_content(self, context, cached_content):
        try:
            attempt = get_attempt(self, context["instance"], context["user"])
        except NoAttemptException:
            return cached_content

        # make a copy of context
        context = context.flatten()

        if choice := attempt.get_user_task(context["user"]):
            exercise = choice.embedlink.embedded_page
            cached_content["content"] = exercise.get_rendered_content(exercise, context)
            answer_widget = exercise.get_answer_widget(context["instance"].course)
            context["choices"] = exercise.get_choices(exercise, revision=context["revision"])
            cached_content["form"] = answer_widget.render(context)
            if not choice.opened:
                choice.opened = datetime.datetime.now()
                choice.save()

        return cached_content

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
        options.append((
            _("Update evaluations"),
            "examtask-update-evaluations",
            "side-panel",
            reverse("examtask:update_evaluations", kwargs={
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

        try:
            attempt = get_attempt(self, instance, user)
        except NoAttemptException:
            raise cm.InvalidExerciseAnswerException("No open attempt")

        if choice := attempt.get_user_task(user):
            exercise = choice.embedlink.embedded_page
            task_answer = exercise.save_answer(
                exercise, user, ip, answer, files, instance, revision
            )
        else:
            raise cm.InvalidExerciseAnswerException("No assigned task")

        answer_object = UserExamTaskAnswer(
            user=user,
            exercise=self,
            instance=instance,
            revision=revision,
            answerer_ip=ip,
            task_answer=task_answer
        )
        answer_object.save()
        return answer_object

    def check_answer(self, link, user, answer, files, answer_object):
        # proxy checking to the randomized task

        attempt = get_attempt(self, answer_object.instance, user)
        exercise = answer_object.task_answer.exercise
        exercise_link = attempt.get_user_task(user).embedlink

        link.manually_evaluated = exercise_link.manually_evaluated
        link.correct_threshold = exercise_link.correct_threshold

        exercise_evaluation = exercise.check_answer(
            exercise, link, user, answer, files, answer_object.task_answer
        )
        if task_id := exercise_evaluation.get("task_id"):
            answer_object.task_id = task_id
            answer_object.save()

        return exercise_evaluation

    def save_evaluation(self, link, user, evaluation, answer_object):
        attempt = get_attempt(self, answer_object.instance, user)
        exercise = attempt.get_user_task(user).embedlink.embedded_page
        exercise.save_evaluation(exercise, link, user, evaluation, answer_object.task_answer)
        return cm.ContentPage.save_evaluation(self, link, user, evaluation, answer_object)

    def get_user_answers(self, user, instance, ignore_drafts=True):
        return UserExamTaskAnswer.objects.filter(
            exercise=self,
            instance=instance,
            user=user,
        )

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
    task = models.ForeignKey(ExamTask, on_delete=models.RESTRICT)
    task_pool = models.ManyToManyField(
        cm.EmbeddedLink,
        through="ExamTaskToExerciseLink",
        through_fields=("settings", "embedlink"),
        related_name="task_pool"
    )
    avoid_same = models.BooleanField(verbose_name=_("Avoid assigning same task"), default=False)

    def export(self, instance, export_target):
        super().export(instance, export_target)
        for link in self.task_pool:
            link.export(instance, export_target)


class ExamTaskToExerciseManager(models.Manager):

    def get_by_natural_key(self, instance_slug, exam_slug, exercise_slug):
        return self.get(
            settings__instance__slug=instance_slug,
            settings__exam__slug=exam_slug,
            embedlink__embedded_page__slug=exercise_slug,
        )


class ExamTaskToExerciseLink(models.Model, ExportImportMixin):

    class Meta:
        unique_together = ("settings", "embedlink")

    objects = ExamTaskToExerciseManager()

    settings = models.ForeignKey(ExamTaskSettings, on_delete=models.CASCADE)
    embedlink = models.ForeignKey(cm.EmbeddedLink, on_delete=models.CASCADE, null=True)

    def natural_key(self):
        return [settings.exam.slug, settings.instance.slug, embedlink.embedded_page.slug]


class UserExamTaskAnswer(cm.UserAnswer):

    exercise = models.ForeignKey(
        ExamTask, blank=True, null=True, on_delete=models.SET_NULL
    )
    task_answer = models.OneToOneField(
        cm.UserAnswer, on_delete=models.CASCADE, related_name="exam_proxy_answer"
    )



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
    parent = models.ForeignKey(
        cm.ContentPage, null=True, on_delete=models.SET_NULL,
        related_name="child_examtask_attempt_set"
    )
    start = models.DateTimeField()
    end = models.DateTimeField()
    user = models.ForeignKey(cm.User, null=True, blank=True, on_delete=models.CASCADE)

    def assign_tasks(self):
        try:
            settings = ExamTaskSettings.objects.get(
                instance=self.instance,
                task=self.task,
            )
        except ExamTaskSettings.DoesNotExist:
            return

        task_qs = settings.task_pool.get_queryset()
        task_pool = list(task_qs)

        if self.user is not None:
            users = [self.user]
        else:
            users = self.instance.enrolled_users.get_queryset()

        for user in users:
            try:
                choice = ExamTaskChoice.objects.get(attempt=self, user=user)
            except ExamTaskChoice.DoesNotExist:
                choice = ExamTaskChoice(attempt=self, user=user)

            # Don't reassign new task if student has already opened the exam task
            if choice.opened:
                continue

            personal_pool = task_pool
            if settings.avoid_same:
                past_choices = ExamTaskChoice.objects.filter(
                    attempt__task=self.task,
                    user=user
                )
                if remaining := task_qs.exclude(exercise__in=past_choices):
                    personal_pool = list(remaining)

            embedlink = random.choice(personal_pool)
            choice.embedlink=embedlink
            choice.save()

    def get_user_task(self, user):
        try:
            choice = ExamTaskChoice.objects.get(user=user, attempt=self)
        except ExamTaskChoice.DoesNotExist:
            return None

        return choice

    def reset_tasks(self):
        ExamTaskChoice.objects.filter(
            attempt=self,
            opened=None,
        ).delete()



class ExamTaskChoice(models.Model):

    class Meta:
        unique_together = ("user", "attempt")

    embedlink = models.ForeignKey(cm.EmbeddedLink, on_delete=models.CASCADE)
    user = models.ForeignKey(cm.User, on_delete=models.CASCADE)
    attempt = models.ForeignKey(ExamTaskAttempt, on_delete=models.CASCADE)
    opened = models.DateTimeField(null=True)


cm.ContentPage.register_content_type(
    "EXAM_TASK", ExamTask, None, None
)

def clone_models(old_instance, new_instance):
    for settings in ExamTaskSettings.objects.filter(instance=old_instance):
        tasklinks = list(ExamTaskToExerciseLink.objects.filter(settings=settings))
        settings.pk = None
        settings.instance = new_instance
        settings.save()

        for link in tasklinks:
            link.pk = None
            link.embedlink = cm.EmbeddedLink.objects.get(
                instance=new_instance,
                parent=link.embedlink.parent,
                embedded_page=link.embedlink.embedded_page
            )
            link.settings = settings
            link.save()

def get_import_list():
    return [
        ExamTask,
        ExamTaskSettings,
        ExamTaskToExerciseLink
    ]
