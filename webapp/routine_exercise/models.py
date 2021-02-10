import datetime

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.contrib.postgres.fields import ArrayField, JSONField
from django.template import loader
from django.urls import reverse
from django.utils.text import slugify

from courses.models import ContentPage, CourseInstance, Evaluation, User

from utils.files import get_testfile_path, upload_storage
import courses.markupparser as markupparser


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
        parents = ContentPage.objects.filter(embedded_pages=self).distinct()
        for instance in CourseInstance.objects.filter(Q(contentgraph__content=self) | Q(contentgraph__content__embedded_pages=self), frozen=False).distinct():
            self.update_embedded_links(instance)
            for parent in parents:
                parent.regenerate_cache(instance)

    def get_rendered_content(self, context):
        content = ContentPage._get_rendered_content(self, context)
        t = loader.get_template("routine_exercise/routine-exercise-content-extra.html")
        return content + t.render(context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

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
            ).prefetch_related("question", "question__template")
        else:
            answers = RoutineExerciseAnswer.objects.filter(
                question__exercise=self,
                question__user=user,
                question__instance=instance
            ).prefetch_related("question", "question__template")
            
        return answers
            
        history = []
        for answer in answers:
            rendered_text = answer.question.template.content.format(
                **answer.question.generated_json["formatdict"]
            )
            marked_text = "".join(
                markupparser.MarkupParser.parse(rendered_text)
            ).strip()
            history.append({
                "question": marked_text,
                "answer": answer.given_answer,
                "correct": answer.correct,
                "answer_date": answer.date_answered,
            })
            
        return history

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
    answer_date = models.DateTimeField()
    given_answer = models.TextField(blank=True)


class RoutineExerciseProgress(models.Model):
    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    progress = models.CharField(max_length=255)

