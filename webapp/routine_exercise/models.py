import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import ArrayField, JSONField
from django.urls import reverse
from django.utils.text import slugify

from courses.models import ContentPage, CourseInstance, Evaluation, User

from utils.files import get_testfile_path, upload_storage


class RoutineExercise(ContentPage):

    template = "routine_exercise/routine-exercise.html"
    answers_template = "routine_exercise/user-answers.html"

    class Meta:
        verbose_name = "routine exercise"
        proxy = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "ROUTINE_EXERCISE"
        super().save(*args, **kwargs)
        RoutineExerciseQuestion.objects.filter(
            exercise=self,
            routineexerciseanswer=None
        ).delete()
        instances = CourseInstance.objects.filter(
            Q(contentgraph__content=self) | Q(contentgraph__content__embedded_pages=self),
            frozen=False
        )
        for instance in instances:
            self.update_embedded_links(instance)

    def get_choices(self, revision=None):
        return

    def get_admin_change_url(self):
        adminized_type = self.content_type.replace("_", "").lower()
        return reverse("admin:routine_exercise_%s_change" % (adminized_type), args=(self.id,))

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = RoutineExerciseAnswer.objects.filter(
                question__exercise=self,
                question__user=user
            )
        else:
            answers = RoutineExerciseAnswer.objects.filter(
                question__exercise=self,
                question__user=user,
                question__instance=instance
            )
        return answers

    def get_user_evaluation(self, user, instance, check_group=True):
        if instance is None:
            evaluations = Evaluation.objects.filter(useranswer__userrepeatedtemplateexerciseanswer__exercise=self, useranswer__user=user)
        else:
            evaluations = Evaluation.objects.filter(useranswer__userrepeatedtemplateexerciseanswer__exercise=self, useranswer__user=user, useranswer__instance=instance)
        correct = evaluations.filter(correct=True).count() > 0
        if correct:
            return "correct"

        if not self.evaluation_group or not check_group:
            return "incorrect" if evaluations else "unanswered"

        group = RoutineExercise.objects.filter(evaluation_group=self.evaluation_group).exclude(id=self.id)
        for exercise in group:
            if exercise.get_user_evaluation(exercise, user, instance, False) == "correct":
                return "credited"

        return "incorrect" if evaluations else "unanswered"

    def save_answer(self, user, ip, answer, files, instance, revision):
        pass

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        pass

    def save_evaluation(self, user, evaluation, answer_object):
        pass


class RoutineExerciseBackendFile(models.Model):
    class Meta:
        verbose_name = "routine exercise backend file"
        verbose_name_plural = "routine exercise backend files"

    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, blank=True)
    fileinfo = models.FileField(max_length=255, upload_to=get_testfile_path, storage=upload_storage)


class RoutineExerciseBackendCommand(models.Model):
    class Meta:
        verbose_name = "routine exercise backend command"

    exercise = models.OneToOneField(RoutineExercise, on_delete=models.CASCADE)
    command = models.TextField()


class RoutineExerciseTemplate(models.Model):
    class Meta:
        verbose_name = "routine exercise template"
        verbose_name_plural = "routine exercise templates"

    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    content = models.TextField()
    question_class = models.PositiveIntegerField()


class RoutineExerciseQuestion(models.Model):
    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(null=True)
    language_code = models.CharField(max_length=7)
    question_class = models.PositiveIntegerField()
    template=models.ForeignKey(RoutineExerciseTemplate, null=True, on_delete=models.SET_NULL)
    generated_json = JSONField()
    date_generated = models.DateTimeField()


class RoutineExerciseAnswer(models.Model):

    question = models.OneToOneField(RoutineExerciseQuestion, on_delete=models.CASCADE)
    correct = models.NullBooleanField(null=True)
    date_answered = models.DateTimeField()
    given_answer = models.TextField(blank=True)


class RoutineExerciseProgress(models.Model):
    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    progress = models.CharField(max_length=255)

