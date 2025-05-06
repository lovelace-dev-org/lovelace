from django.core import serializers
from django.db import models
from django.utils.translation import gettext_lazy as _
from reversion.models import Version
from courses.models import ContentPage, CourseInstance, SlugManager
from utils.data import (
    export_json, serialize_single_python, serialize_many_python
)
from utils.management import ExportImportMixin, get_prefixed_slug


class FaqQuestion(models.Model, ExportImportMixin):
    objects = SlugManager()

    question = models.TextField(verbose_name=_("Question"))
    answer = models.TextField(verbose_name=_("Answer"))
    hook = models.SlugField(max_length=255, blank=False, allow_unicode=True, unique=True)
    origin = models.ForeignKey("courses.Course", null=True, on_delete=models.SET_NULL)
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )

    def natural_key(self):
        return (self.slug, )

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.origin, "hook", translated=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"({self.hook}) {self.question}"


class FaqLinkManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, instance_slug, question_slug):
        return self.get(
            exercise__slug=exercise_slug,
            instance__slug=instance_slug,
            question__slug=question_slug,
        )


class FaqToInstanceLink(models.Model, ExportImportMixin):
    objects = FaqLinkManager()

    question = models.ForeignKey(FaqQuestion, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    exercise = models.ForeignKey(ContentPage, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(
        verbose_name="Revision to display", blank=True, null=True
    )

    class Meta:
        unique_together = ("instance", "question", "exercise")

    def natural_key(self):
        return [self.exercise.slug, self.instance.slug, self.question.slug]

    def freeze(self, freeze_to=None):
        if self.revision is None:
            latest = Version.objects.get_for_object(self.question).latest("revision__date_created")
            self.revision = latest.revision_id

    def set_instance(self, instance):
        self.instance = instance


def export_models(instance, export_target):
    faq_links = (
        FaqToInstanceLink.objects.filter(instance=instance)
        .order_by("question__id")
        .distinct("question__id")
    )
    for faq_link in faq_links:
        faq_link.question.export(instance, export_target)
        faq_link.export(instance, export_target)

def get_import_list():
    return [
        FaqQuestion,
        FaqToInstanceLink,
    ]
