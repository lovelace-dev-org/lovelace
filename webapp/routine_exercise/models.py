from django.core import serializers
from django.db import models
from django.db.models import Q, JSONField
from django.template import loader
from django.urls import reverse
from django.utils.text import slugify

from courses.models import ContentPage, CourseInstance, User

from utils.data import export_json, export_files, serialize_many_python, serialize_single_python
from utils.files import get_testfile_path, upload_storage
from utils.management import ExportImportMixin


class RoutineExercise(ContentPage):
    template = "routine_exercise/routine-exercise.html"
    answers_template = "routine_exercise/user-answers.html"
    answer_table_classes = "fixed"

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
        RoutineExerciseQuestion.objects.filter(exercise=self, routineexerciseanswer=None).delete()
        parents = ContentPage.objects.filter(embedded_pages=self).distinct()
        for instance in CourseInstance.objects.filter(
            Q(contentgraph__content=self) | Q(contentgraph__content__embedded_pages=self),
            frozen=False,
        ).distinct():
            self.update_embedded_links(instance)
            for parent in parents:
                parent.regenerate_cache(instance)

    def get_rendered_content(self, context):
        content = ContentPage._get_rendered_content(self, context)
        t = loader.get_template("routine_exercise/routine-exercise-content-extra.html")
        return content + [("extra", t.render(context), -1, 0)]

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def get_choices(self, revision=None):
        return

    def get_admin_change_url(self):
        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:routine_exercise_{adminized_type}_change", args=(self.id,))

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = RoutineExerciseAnswer.objects.filter(
                question__exercise=self, question__user=user
            ).prefetch_related("question", "question__template")
        else:
            answers = RoutineExerciseAnswer.objects.filter(
                question__exercise=self, question__user=user, question__instance=instance
            ).prefetch_related("question", "question__template")

        return answers

    def re_evaluate(self, user, instance):
        from utils.exercise import update_completion

        progress = RoutineExerciseProgress.objects.filter(
            exercise=self, user=user, instance=instance, completed=True
        ).first()

        if not progress:
            return

        evaluation = {
            "evaluation": True,
            "points": progress.points,
            "max": progress.max_points,
        }
        try:
            answer_date = (
                RoutineExerciseAnswer.objects.filter(
                    question__exercise=self,
                    question__user=user,
                    question__instance=instance,
                    correct=True,
                )
                .order_by("-answer_date")
                .first()
                .answer_date
            )
        except AttributeError:
            return

        update_completion(self, instance, user, evaluation, answer_date)

    def save_answer(self, user, ip, answer, files, instance, revision):
        pass

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        pass

    def save_evaluation(self, user, evaluation, answer_object):
        pass

    def export(self, instance, export_target):
        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_single_python(self.routineexercisebackendcommand),
            f"{self.slug}_command",
            export_target,
        )
        export_json(
            serialize_many_python(self.routineexercisetemplate_set.get_queryset()),
            f"{self.slug}_templates",
            export_target,
        )
        for backend in RoutineExerciseBackendFile.objects.filter(exercise=self):
            backend.export(instance, export_target)


class RoutineBackendManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, filename):
        return self.get(exercise__slug=exercise_slug, filename=filename)

class RoutineExerciseBackendFile(models.Model, ExportImportMixin):
    class Meta:
        verbose_name = "routine exercise backend file"
        verbose_name_plural = "routine exercise backend files"

    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, blank=True)
    fileinfo = models.FileField(max_length=255, upload_to=get_testfile_path, storage=upload_storage)

    def natural_key(self):
        return (self.exercise.slug, self.filename)

    def export(self, instance, export_target):
        super().export(instance, export_target)
        export_files(self, export_target, "backend")

class RoutineCommandManager(models.Manager):

    def get_by_natural_key(self, exercise_slug):
        return self.get(exercise__slug=exercise_slug)


class RoutineExerciseBackendCommand(models.Model):
    class Meta:
        verbose_name = "routine exercise backend command"

    objects = RoutineCommandManager()

    exercise = models.OneToOneField(RoutineExercise, on_delete=models.CASCADE)
    command = models.TextField()

    def natural_key(self):
        return [self.exercise.slug]


class RoutineTemplateManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, variant, question_class):
        return self.get(
            exercise__slug=exercise_slug,
            variant=variant,
            question_class=question_class
        )


class RoutineExerciseTemplate(models.Model):
    class Meta:
        verbose_name = "routine exercise template"
        verbose_name_plural = "routine exercise templates"

    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    content = models.TextField()
    question_class = models.PositiveIntegerField()
    variant = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        if self.variant is None:
            previous = RoutineExerciseTemplate.objects.filter(
                exercise=self.exercise,
                question_class=self.question_class
            ).order_by("-variant").first()
            if previous and previous.variant is not None:
                self.variant = previous.variant + 1
            else:
                self.variant = 0
        super().save(*args, **kwargs)


class RoutineExerciseQuestion(models.Model):
    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(null=True)
    language_code = models.CharField(max_length=7)
    question_class = models.PositiveIntegerField()
    template = models.ForeignKey(RoutineExerciseTemplate, null=True, on_delete=models.SET_NULL)
    generated_json = JSONField()
    date_generated = models.DateTimeField()


class RoutineExerciseAnswer(models.Model):
    question = models.OneToOneField(RoutineExerciseQuestion, on_delete=models.CASCADE)
    correct = models.BooleanField(null=True)
    answer_date = models.DateTimeField()
    given_answer = models.TextField(blank=True)
    task_id = models.CharField(max_length=36, null=True, blank=True)


class RoutineExerciseProgress(models.Model):
    class Meta:
        unique_together = ("exercise", "instance", "user")

    exercise = models.ForeignKey(RoutineExercise, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, null=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    completed = models.BooleanField(default=False)
    progress = models.CharField(max_length=255)
    points = models.DecimalField(default=0, max_digits=5, decimal_places=2)
    max_points = models.PositiveIntegerField(default=1)


ContentPage.register_content_type(
    "ROUTINE_EXERCISE", RoutineExercise, RoutineExerciseAnswer
)

def export_models(instance, export_target):
    pass

def get_import_list():
    return [
        RoutineExercise,
        RoutineExerciseBackendCommand,
        RoutineExerciseBackendFile,
        RoutineExerciseTemplate
    ]
