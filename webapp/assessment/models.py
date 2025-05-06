from django.core import serializers
from django.db import models
from reversion.models import Version
from courses.models import SlugManager
from utils.archive import find_latest_version, get_archived_instances
from utils.data import (
    export_json, serialize_single_python, serialize_many_python
)
from utils.management import get_prefixed_slug


class AssessmentToExerciseLink(models.Model):
    instance = models.ForeignKey("courses.CourseInstance", on_delete=models.CASCADE)
    exercise = models.ForeignKey("courses.ContentPage", on_delete=models.CASCADE)
    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(blank=True, null=True)

    def natural_key(self):
        return self.sheet.natural_key() + [self.exercise.slug]

    def freeze(self, freeze_to):
        try:
            version = find_latest_version(self.sheet, freeze_to)
        except Version.DoesNotExist:
            self.delete()
            return

        self.revision = version.revision_id
        self.save()

    def calculate_max_score(self):
        if self.revision is None:
            q = self.sheet.assessmentbullet_set.get_queryset().aggregate(
                max_score=models.Sum("point_value")
            )
            return q["max_score"]

        old_sheet = get_archived_instances(self.sheet, self.revision)
        bullets = old_sheet["assessmentbullet_set"]
        return sum(bullet.point_value for bullet in bullets)

    def export(self, instance, export_target):
        document = serialize_single_python(self)
        name = "_".join(self.natural_key())
        export_json(document, name, export_target)

    def set_instance(self, instance):
        self.instance = instance


class AssessmentSheet(models.Model):
    # Translatable fields
    objects = SlugManager()

    title = models.CharField(max_length=255)
    origin = models.ForeignKey("courses.Course", on_delete=models.CASCADE)
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.origin, "title")
        super().save(*args, **kwargs)

    def natural_key(self):
        return [self.slug]

    def export(self, instance, export_target):
        document = serialize_single_python(self)
        name = "_".join(self.natural_key())
        export_json(document, name, export_target)
        for section in self.assessmentsection_set.get_queryset():
            section.export(instance, export_target)
        links = AssessmentToExerciseLink.objects.filter(
            sheet=self,
            instance=instance,
        )
        for link in links:
            link.export(instance, export_target)


class AssessmentSectionManager(models.Manager):

    def get_by_natural_key(self, sheet_slug, ordinal):
        return self.get(
            sheet__slug=sheet_slug,
            ordinal_number=ordinal
        )


class AssessmentSection(models.Model):
    objects = AssessmentSectionManager()

    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    ordinal_number = models.PositiveSmallIntegerField()

    def natural_key(self):
        return self.sheet.natural_key() + [str(self.ordinal_number)]

    def __str__(self):
        return self.title

    def export(self, instance, export_target):
        document = serialize_single_python(self)
        name = "_".join(self.natural_key())
        export_json(document, name, export_target)
        export_json(
            serialize_many_python(self.assessmentbullet_set.get_queryset()),
            f"{name}_bullets",
            export_target,
        )


class AssessmentBulletManager(models.Manager):

    def get_by_natural_key(self, sheet_slug, section_ordinal, ordinal):
        return self.get(
            sheet__slug=sheet_slug,
            section__ordinal_number=section_ordinal,
            ordinal_number=ordinal
        )


class AssessmentBullet(models.Model):
    sheet = models.ForeignKey("AssessmentSheet", on_delete=models.CASCADE)
    point_value = models.FloatField(blank=False, null=False)
    ordinal_number = models.PositiveSmallIntegerField()
    section = models.ForeignKey("AssessmentSection", on_delete=models.CASCADE)

    # Translatable fields
    title = models.CharField(max_length=255)
    tooltip = models.TextField(blank=True, default="")

    def natural_key(self):
        return list(self.section.natural_key()) + [str(self.ordinal_number)]


def export_models(instance, export_target):
    links = (
        AssessmentToExerciseLink.objects.filter(instance=instance)
        .order_by("sheet__id")
        .distinct("sheet__id")
    )
    for link in links:
        link.sheet.export(instance, export_target)

def get_import_list():
    return [
        AssessmentSheet,
        AssessmentSection,
        AssessmentBullet,
        AssessmentToExerciseLink,
    ]
