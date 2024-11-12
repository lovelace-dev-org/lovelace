"""Django database models for courses."""

import datetime
import itertools
import operator
import re
import os
import uuid
from collections import defaultdict
from fnmatch import fnmatch
from html import escape

from django.conf import settings
from django.core import serializers
from django.core.files.base import ContentFile
from django.db import models, transaction
from django.db.models import Q, Max, JSONField
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.urls import reverse
from django.core.cache import cache
from django.template import loader
from django.utils import translation
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
import django.conf

from model_utils.managers import InheritanceManager
from reversion.models import Version

import pygments
import magic

import feedback.models
from lovelace import plugins as lovelace_plugins
from utils.data import (
    export_json, export_files, serialize_single_python, serialize_many_python
)
from utils.files import (
    get_answerfile_path,
    get_file_upload_path,
    get_image_upload_path,
    get_instancefile_path,
    get_testfile_path,
    upload_storage,
)
from utils.archive import get_archived_field, get_single_archived
from utils.management import (
    ExportImportMixin,
    freeze_context_link,
    get_prefixed_slug,
)


class RollbackRevert(Exception):
    pass



class About(models.Model):

    content = models.TextField(blank=True, null=True)


# ^
# |
# META
# USER RELATED
# |
# V


# TODO: Extend the registration system to allow users to enter the profile data!
# TODO: Separate profiles for students and teachers
class UserProfile(models.Model):
    """User profile, which extends the Django's User model."""

    # For more information, see:
    # https://docs.djangoproject.com/en/dev/topics/auth/#storing-additional-information-about-users
    # http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    student_id = models.CharField(max_length=36, verbose_name="Student ID", blank=True, null=True)
    study_program = models.CharField(
        verbose_name="Study program", max_length=80, blank=True, null=True
    )
    enrollment_year = models.PositiveSmallIntegerField(
        verbose_name="Year of enrollment", blank=True, null=True
    )

    def __str__(self):
        return f"{self.user}'s profile"

    def save(self, *args, **kwargs):
        # To prevent 'column user_id is not unique' error from creating a new
        # user in admin interface ( http://stackoverflow.com/a/2813728 )
        try:
            existing = UserProfile.objects.get(user=self.user)
            self.id = existing.id
        except UserProfile.DoesNotExist:
            pass
        models.Model.save(self, *args, **kwargs)


def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


post_save.connect(create_user_profile, sender=User, dispatch_uid="create_user_profile_lovelace")


class StudentGroup(models.Model):
    name = models.CharField(max_length=64, verbose_name=_("Group name"))
    instance = models.ForeignKey("CourseInstance", on_delete=models.CASCADE)
    supervisor = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="supervised_group"
    )
    members = models.ManyToManyField(User)


class GroupInvitation(models.Model):
    class Meta:
        unique_together = ("group", "user")

    group = models.ForeignKey("StudentGroup", on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_invitation")


class SavedMessage(models.Model):
    class Meta:
        unique_together = ("course", "handle")

    course = models.ForeignKey("Course", null=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    handle = models.CharField(max_length=127, verbose_name="Save as")
    title = models.CharField(max_length=255, blank=True, default="")  # Translate
    content = models.TextField(blank=True, default="")  # Translate

    def serialize_translated(self):
        data = {
            "handle": self.handle,
        }
        for lang_code, __ in settings.LANGUAGES:
            data[f"title_{lang_code}"] = getattr(self, f"title_{lang_code}", "")
            data[f"content_{lang_code}"] = getattr(self, f"content_{lang_code}", "")
        return data

    def _join_translated_fields(self, field, separator):
        languages = sorted(
            settings.LANGUAGES,
            key=lambda x: x[0] == settings.MODELTRANSLATION_DEFAULT_LANGUAGE,
            reverse=True,
        )
        values = []
        for lang_code, __ in languages:
            content = getattr(self, f"{field}_{lang_code}", "")
            if content:
                values.append(content)
        return separator.join(values)

    def render_title(self, lang_code=None):
        if lang_code is None:
            return self._join_translated_fields("title", " / ")
        return getattr(self, f"title_{lang_code}", "")

    def render_content(self, lang_code=None):
        if lang_code is None:
            return self._join_translated_fields("content", "\n\n--\n\n")
        return getattr(self, f"title_{lang_code}", "")


class DeadlineExemption(models.Model):

    class Meta:
        unique_together = ("user", "contentgraph")

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    contentgraph = models.ForeignKey("ContentGraph", on_delete=models.CASCADE)
    new_deadline = models.DateTimeField(null=True)


# ^
# |
# USER RELATED
# COURSE LEVEL
# |
# V

class SlugManager(models.Manager):

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class Course(models.Model):
    """
    Describes the metadata for a course.
    """

    objects = SlugManager()

    name = models.CharField(max_length=255)  # Translate
    code = models.CharField(
        verbose_name="Course code",
        help_text="Course code, for e.g. universities",
        max_length=64,
        blank=True,
        null=True,
    )
    credits = models.DecimalField(
        verbose_name="Course credits",
        help_text="How many credits does the course " "yield on completion, for e.g. universities",
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
    )
    description = models.TextField(blank=True, null=True)  # Translate
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )
    prerequisites = models.ManyToManyField(
        "Course", verbose_name="Prerequisite courses", blank=True
    )
    staff_group = models.ForeignKey(Group, null=True, on_delete=models.SET_NULL)
    main_responsible = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    staff_course = models.BooleanField(
        default=False,
        verbose_name="Staff only course",
        help_text="Staff only courses will not be shown on the front page unless the user is staff",
    )
    prefix = models.CharField(max_length=4, unique=True)
    # TODO: Create an instance automatically, if none exists

    def natural_key(self):
        return [self.slug]

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        return slugify(self.name, allow_unicode=True)

    def get_instances(self):
        return self.courseinstance_set.all().order_by("-start_date")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



class CourseEnrollment(models.Model):
    class Meta:
        unique_together = ("instance", "student")

    ENROLLMENT_STATE_CHOICES = (
        ("WAITING", "Waiting"),
        ("PROCESSING", "Processing"),
        ("ACCEPTED", "Accepted"),
        ("EXPELLED", "Expelled"),
        ("DENIED", "Denied"),
        ("WITHDRAWN", "Withdrawn"),
        ("COMPLETED", "Completed"),
        ("TRANSFERED", "Transfered"),
    )

    instance = models.ForeignKey("CourseInstance", on_delete=models.CASCADE)
    student = models.ForeignKey(User, on_delete=models.CASCADE)

    enrollment_date = models.DateTimeField(auto_now_add=True)
    application_note = models.TextField(blank=True)  # The student can write an application
    enrollment_state = models.CharField(
        max_length=11, default="WAITING", choices=ENROLLMENT_STATE_CHOICES
    )
    enrollment_note = models.TextField(blank=True)  # The teacher can write a rationale

    def is_enrolled(self):
        return self.enrollment_state == "ACCEPTED"

    @staticmethod
    def get_enrolled_instances(instance, user, exclude_current=False):
        enrollments = CourseEnrollment.objects.filter(
            student=user,
            instance__course=instance.course,
        ).select_related("instance")
        if exclude_current:
            enrollments = enrollments.exclude(instance=instance)
        return [e.instance for e in enrollments]


class CourseInstance(models.Model):
    """
    A running instance of a course. Contains details about the start and end
    dates of the course.
    """

    objects = SlugManager()

    name = models.CharField(max_length=255)  # Translate
    email = models.EmailField(blank=True)  # Translate
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )
    course = models.ForeignKey("Course", on_delete=models.CASCADE)

    start_date = models.DateTimeField(
        verbose_name="Date and time on which the course begins", blank=True, null=True
    )
    end_date = models.DateTimeField(
        verbose_name="Date and time on which the course ends", blank=True, null=True
    )
    active = models.BooleanField(verbose_name="Force this instance active", default=False)

    notes = models.CharField(
        max_length=256, verbose_name="Tags for this instance (comma-separated)", blank=True
    )  # Translate
    enrolled_users = models.ManyToManyField(
        User, blank=True, through="CourseEnrollment", through_fields=("instance", "student")
    )
    manual_accept = models.BooleanField(
        verbose_name="Teachers accept enrollments manually", default=False
    )

    frontpage = models.ForeignKey("Lecture", blank=True, null=True, on_delete=models.SET_NULL)
    frozen = models.BooleanField(verbose_name="Freeze this instance", default=False)
    visible = models.BooleanField(verbose_name="Is this course visible to students", default=True)
    content_license = models.CharField(max_length=255, blank=True)
    license_url = models.CharField(max_length=255, blank=True)
    primary = models.BooleanField(verbose_name="Set this instance as primary.", default=False)
    welcome_message = models.TextField(
        verbose_name="Automatic welcome message for accepted enrollments", blank=True
    )
    max_group_size = models.PositiveSmallIntegerField(null=True, blank=True)

    def natural_key(self):
        return [self.slug]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._was_frozen = self.frozen
        self._was_primary = self.primary

    def is_active(self):
        try:
            return self.start_date <= datetime.datetime.now() <= self.end_date
        except TypeError:
            return True

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        return get_prefixed_slug(self, self.course, "name")

    def user_enroll_status(self, user):
        if not user.is_active:
            return None
        try:
            status = self.courseenrollment_set.get(student=user).enrollment_state
            return status
        except CourseEnrollment.DoesNotExist as e:
            return None

    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        super().save(*args, **kwargs)

        if not self._was_primary and self.primary:
            for instance in CourseInstance.objects.filter(course=self.course).exclude(pk=self.pk):
                was_primary = instance.primary
                instance.primary = False
                instance.save()
                if was_primary:
                    instance.clear_content_tree_cache(regen_frozen=True)
            self.clear_content_tree_cache(regen_frozen=True)


    def get_content_tree(self, lang_code=None, staff=False):
        current_lang = translation.get_language()
        if lang_code is not None:
            translation.activate(lang_code)
        else:
            lang_code = current_lang

        cache_key = f"{self.slug}_tree_{lang_code}"
        if staff:
            cache_key += "_staff"

        cached_tree = cache.get(cache_key)
        if cached_tree:
            return cached_tree

        if staff:
            nodes = ContentGraph.objects.filter(instance=self, ordinal_number__gt=0)
        else:
            nodes = ContentGraph.objects.filter(instance=self, ordinal_number__gt=0, visible=True)

        nodes = nodes.select_related("parentnode", "content").defer("content__content")
        embed_links = (
            EmbeddedLink.objects.filter(instance=self)
            .select_related("embedded_page")
            .defer("embedded_page__content")
        )
        embeds_by_parent = defaultdict(dict)
        for link in embed_links:
            task_group = link.embedded_page.evaluation_group
            try:
                embeds_by_parent[link.parent_id][task_group].append(
                    (link.embedded_page_id, link.embedded_page.default_points)
                )
            except KeyError:
                embeds_by_parent[link.parent_id][task_group] = [
                    (link.embedded_page_id, link.embedded_page.default_points)
                ]

        nodes = list(nodes.order_by("parentnode"))
        ordered = []
        for node in nodes:
            ordinals = [node.ordinal_number]
            parent_node = node.parentnode
            while parent_node is not None:
                ordinals.insert(0, parent_node.ordinal_number)
                parent_node = parent_node.parentnode

            ordered.append((ordinals, node))

        ordered.sort()
        tree = []
        level = 0
        for ordinals, node in ordered:
            while len(ordinals) != level:
                if len(ordinals) > level:
                    tree.append({"content": mark_safe(">")})
                    level += 1
                elif len(ordinals) < level:
                    tree.append({"content": mark_safe("<")})
                    level -= 1

            page_count = node.content.count_pages(self)
            embeds = embeds_by_parent[node.content_id]
            embedded_count = max(len(embeds) - 1, 0) + len(embeds.get("", []))
            page_score = (
                sum(task[1] for task in embeds.get("", []))
                + sum(embeds[tag][0][1] for tag in embeds if tag)
            )

            tree.append({
                "node_id": node.id,
                "content": node.content.name,
                "url": reverse("courses:content", kwargs={
                    "course": self.course,
                    "instance": self,
                    "content": node.content
                }),
                "visible": node.visible,
                "require_enroll": node.require_enroll,
                "page_count": page_count,
                "deadline": node.deadline,
                "embedded_count": embedded_count,
                "page_score": page_score,
                "embeds": embeds,
                "weight": node.score_weight,
            })
        while level > 0:
            tree.append({"content": mark_safe("<")})
            level -= 1

        cache.set(cache_key, tree, timeout=None)

        if lang_code is not None:
            translation.activate(current_lang)

        return tree

    def clear_content_tree_cache(self, regen_frozen=False):
        if self.frozen and not regen_frozen:
            return

        for lang_code, _ in settings.LANGUAGES:
            cache.delete(f"{self.slug}_tree_{lang_code}")
            cache.delete(f"{self.slug}_tree_{lang_code}_staff")

    def freeze(self, freeze_to=None):
        """
        Freezes the course instance by creating copies of content graph links
        and setting their revision to latest version that predates freeze_to
        (latest version if it is None). Embedded links and instance file links
        are also updated in a similar way.
        """

        contents = ContentGraph.objects.filter(instance=self)

        for content_link in contents:
            content_link.freeze(freeze_to)
            content_link.content.update_embedded_links(self, content_link.revision)

        embedded_links = EmbeddedLink.objects.filter(instance=self)
        for link in embedded_links:
            link.freeze(freeze_to)

        media_links = CourseMediaLink.objects.filter(instance=self)
        for link in media_links:
            link.freeze(freeze_to)

        ifile_links = InstanceIncludeFileToInstanceLink.objects.filter(instance=self)
        for link in ifile_links:
            link.freeze(freeze_to)

        term_links = TermToInstanceLink.objects.filter(instance=self)
        for link in term_links:
            link.freeze(freeze_to)

        from faq.models import FaqToInstanceLink

        faq_links = FaqToInstanceLink.objects.filter(instance=self)
        for link in faq_links:
            link.freeze(freeze_to)

        from assessment.models import AssessmentToExerciseLink

        assessment_links = AssessmentToExerciseLink.objects.filter(instance=self)
        for link in assessment_links:
            link.freeze(freeze_to)

        contents = ContentGraph.objects.filter(instance=self)
        frontpage = None
        for content_link in contents:
            content_link.content.regenerate_cache(self)
            if content_link.ordinal_number == 0:
                frontpage = content_link.content

        self.frontpage = frontpage
        self.frozen = True

    def export(self, export_target):
        document = serialize_single_python(self)
        export_json(document, self.slug, export_target)
        export_json(
            serialize_single_python(self.course),
            self.course.slug,
            export_target
        )

        for cg in ContentGraph.objects.filter(instance=self):
            cg.export(export_target)

        for term_link in TermToInstanceLink.objects.filter(instance=self):
            term_link.term.export(self, export_target)
            term_link.export(self, export_target)

        for ifile_link in InstanceIncludeFileToInstanceLink.objects.filter(instance=self):
            ifile_link.export(self, export_target)
            ifile_link.include_file.export(self, export_target)

        embeds = (
            EmbeddedLink.objects.filter(instance=self)
            .order_by("embedded_page__id")
        )
        media = (
            CourseMediaLink.objects.filter(instance=self)
            .order_by("media__id")
        )
        for embed_link in embeds:
            embed_link.export(self, export_target)
        for embed_link in embeds.distinct("embedded_page__id"):
            embed_link.embedded_page.export(embed_link.embedded_page, self, export_target)
        for media_link in media:
            media_link.export(self, export_target)
        for media_link in media.distinct("media__id"):
            media_link.media.export(self, export_target)
            CourseMedia.objects.get_subclass(id=media_link.media.id).export(self, export_target)

        for module in lovelace_plugins["export"]:
            module.models.export_models(self, export_target)



    def finalize_import(self, document, pk_map):
        pass

    def __str__(self):
        return self.name

    def get_identifying_str(self):
        return f"{self.course.name} / {self.name}"

    def split_notes(self):
        if self.notes:
            return self.notes.split(",")
        return []


class GradeThreshold(models.Model):
    instance = models.ForeignKey(
        "CourseInstance", null=False, blank=False, on_delete=models.CASCADE
    )
    threshold = models.PositiveSmallIntegerField(verbose_name="Score threshold")
    grade = models.CharField(
        max_length=4,
    )


class ContextLinkManager(models.Manager):

    def get_by_natural_key(self, instance_slug, content_slug):
        return self.get(instance__slug=instance_slug, content__slug=content_slug)


class ContentGraph(models.Model):
    """A node in the course tree/graph. Links content into a course."""

    class Meta:
        unique_together = ("content", "instance")
        verbose_name = "content to course link"
        verbose_name_plural = "content to course links"

    objects = ContextLinkManager()

    parentnode = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL)
    content = models.ForeignKey("ContentPage", null=True, blank=True, on_delete=models.RESTRICT)
    instance = models.ForeignKey(
        "CourseInstance", null=False, blank=False, on_delete=models.CASCADE
    )
    responsible = models.ManyToManyField(User, blank=True)
    compulsory = models.BooleanField(
        verbose_name="Must be answered correctly before proceeding to next exercise", default=False
    )
    deadline = models.DateTimeField(
        verbose_name="The due date for completing this exercise", blank=True, null=True
    )
    late_rule = models.CharField(
        verbose_name="Score reduction formula to use for late submissions",
        help_text=_(
            r"Write a mathematical formula. Four placeholders are available.\n"
            r"{q} is obtained score as quotient of max points.\n"
            r"{p} is obtained raw points\n"
            r"{m} is the task's max points\n"
            r"{d} is the amount of days since deadline"
        ),
        max_length=50,
        blank=True,
        null=True,
    )
    score_weight = models.DecimalField(
        verbose_name="Weight multiplier to use in scoring for tasks on this page",
        default=1,
        max_digits=5,
        decimal_places=2,
    )
    scoring_group = models.CharField(
        max_length=32,
        help_text="Scoring group identifier, used for binding together mutually exclusive pages.",
        blank=True,
    )
    publish_date = models.DateTimeField(
        verbose_name="When does this exercise become available", blank=True, null=True
    )
    require_enroll = models.BooleanField(
        verbose_name="Content can only be viewed by enrolled users", default=False
    )
    scored = models.BooleanField(verbose_name="Does this exercise affect scoring", default=True)
    ordinal_number = models.PositiveSmallIntegerField()
    visible = models.BooleanField(verbose_name="Is this content visible to students", default=True)
    revision = models.PositiveIntegerField(
        verbose_name="The specific revision of the content", blank=True, null=True  # null = current
    )
    evergreen = models.BooleanField(verbose_name="This content should not be frozen", default=False)

    def natural_key(self):
        return (self.instance.slug, self.content.slug)

    def get_revision_str(self):
        if self.revision is None:
            return "newest"
        return f"rev. {self.revision}"

    def get_deadline_urgency(self):
        if self.deadline is not None:
            now = datetime.datetime.now()
            if self.deadline < now:
                return "past"

            diff = self.deadline - now
            if diff.days <= 1:
                return "urgent"

            if diff.days <= 7:
                return "near"

            return "normal"
        return ""


    def freeze(self, freeze_to=None):
        freeze_context_link(self, "content", freeze_to)

    def export(self, export_target):
        document = serialize_single_python(self)
        export_json(
            document,
            "_".join(self.natural_key()),
            export_target
        )
        self.content.export(self.content, self.instance, export_target)

    def set_instance(self, instance):
        self.instance = instance

    def __str__(self):
        return f"No. {self.ordinal_number} – {self.content.slug} ({self.get_revision_str()})"


# ^
# |
# COURSE LEVEL
# MEDIA
# |
# V

class MediaManager(InheritanceManager):

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class CourseMedia(models.Model, ExportImportMixin):
    """
    Top level model for embedded media.
    """

    objects = MediaManager()

    name = models.CharField(
        verbose_name="Unique name identifier", max_length=200
    )
    origin = models.ForeignKey("Course", null=True, on_delete=models.SET_NULL)
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )

    def natural_key(self):
        return (self.slug, )

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.origin, "name", translated=False)
        super().save(*args, **kwargs)
        for link in self.coursemedialink_set.get_queryset():
            if not link.instance.frozen:
                link.parent.regenerate_cache(link.instance)


class MediaLinkManager(models.Manager):

    def get_by_natural_key(self, parent_slug, media_slug, instance_slug):
        return self.get(
            parent__slug=parent_slug, media__slug=media_slug, instance__slug=instance_slug
        )



class CourseMediaLink(models.Model, ExportImportMixin):
    """
    Context model for embedded media.
    """

    objects = MediaLinkManager()

    media = models.ForeignKey(CourseMedia, on_delete=models.RESTRICT)
    parent = models.ForeignKey("ContentPage", on_delete=models.CASCADE, null=True)
    instance = models.ForeignKey(
        CourseInstance, verbose_name="Course instance", on_delete=models.CASCADE
    )
    revision = models.PositiveIntegerField(
        verbose_name="Revision to display", blank=True, null=True
    )

    def natural_key(self):
        return [self.parent.slug, self.media.slug, self.instance.slug]

    class Meta:
        unique_together = ("instance", "media", "parent")

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "media", freeze_to)

    def set_instance(self):
        self.instance = instance


class File(CourseMedia):
    """Metadata of an embedded or attached file that an admin has uploaded."""

    # TODO: Make the uploading user the default and don't allow it to change
    date_uploaded = models.DateTimeField(verbose_name="date uploaded", auto_now_add=True)
    typeinfo = models.CharField(max_length=200)
    fileinfo = models.FileField(max_length=255, upload_to=get_file_upload_path)  # Translate
    download_as = models.CharField(
        verbose_name="Default name for the download dialog", max_length=200, null=True, blank=True
    )

    def __str__(self):
        return self.name

    def export(self, instance, export_target):
        super().export(instance, export_target)
        export_files(self, export_target, "media", translate=True)


class Image(CourseMedia):
    """Image"""

    # TODO: Make the uploading user the default and don't allow it to change
    date_uploaded = models.DateTimeField(verbose_name="date uploaded", auto_now_add=True)
    description = models.CharField(max_length=500)  # Translate
    fileinfo = models.ImageField(upload_to=get_image_upload_path)  # Translate

    def __str__(self):
        return self.name

    def serialize_translated(self):
        data = {
            "name": self.name,
        }
        for lang_code, __ in settings.LANGUAGES:
            data[f"description{lang_code}"] = getattr(self, f"description{lang_code}", "")
            data[f"fileinfo_{lang_code}"] = str(getattr(self, f"fileinfo_{lang_code}", ""))
        return data

    def export(self, instance, export_target):
        super().export(instance, export_target)
        export_files(self, export_target, "media", translate=True)


class VideoLink(CourseMedia):
    """Youtube link for embedded videos"""

    # TODO: Make the adding user the default and don't allow it to change
    link = models.URLField()  # Translate
    description = models.CharField(max_length=500)  # Translate

    def __str__(self):
        return self.name


# ^
# |
# MEDIA
# TERMS
# |
# V


class TermLinkManager(models.Manager):

    def get_by_natural_key(self, term_slug, instance_slug):
        return self.get(term__slug=term_slug, instance__slug=instance_slug)


class TermToInstanceLink(models.Model, ExportImportMixin):
    class Meta:
        unique_together = ("instance", "term")

    objects = TermLinkManager()

    term = models.ForeignKey("Term", on_delete=models.RESTRICT)
    instance = models.ForeignKey(
        CourseInstance, verbose_name="Course instance", on_delete=models.CASCADE
    )
    revision = models.PositiveIntegerField(
        verbose_name="Revision to display", blank=True, null=True
    )

    def natural_key(self):
        return self.term.natural_key() + self.instance.natural_key()

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "term", freeze_to)

    def set_instance(self, instance):
        self.instance = instance


class Term(models.Model, ExportImportMixin):
    class Meta:
        unique_together = (
            "origin",
            "name",
        )

    objects = SlugManager()

    name = models.CharField(verbose_name="Term", max_length=200)  # Translate
    origin = models.ForeignKey(Course, verbose_name="Course", null=True, on_delete=models.SET_NULL)
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )
    description = models.TextField()  # Translate

    tags = models.ManyToManyField("TermTag", blank=True)

    def natural_key(self):
        return [self.slug]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.origin, "name")
        super().save(*args, **kwargs)
        for instance in CourseInstance.objects.filter(course=self.origin, frozen=False):
            if not TermToInstanceLink.objects.filter(instance=instance, term=self):
                link = TermToInstanceLink(instance=instance, revision=None, term=self)
                link.save()

    def export(self, instance, export_target):
        super().export(instance, export_target)
        export_json(
            serialize_many_python(self.termalias_set.get_queryset()),
            f"{self.name}_aliases",
            export_target,
        )
        export_json(
            serialize_many_python(self.tags.get_queryset()),
            f"{self.name}_tags",
            export_target,
        )
        export_json(
            serialize_many_python(self.termtab_set.get_queryset()),
            f"{self.name}_tabs",
            export_target,
        )
        export_json(
            serialize_many_python(self.termlink_set.get_queryset()),
            f"{self.name}_links",
            export_target,
        )

    def set_instance(self, instance):
        self.origin = instance.course


class TermAlias(models.Model):
    term = models.ForeignKey(Term, null=True, on_delete=models.CASCADE)
    name = models.CharField(verbose_name="Term", max_length=200)  # Translate

    def natural_key(self):
        return self.term.natural_key() + [self.name]


class TermTagManager(models.Manager):

    def get_by_natural_key(self, export_id):
        return self.get(export_id=export_id)


class TermTag(models.Model):
    objects = TermTagManager()

    name = models.CharField(verbose_name="Term", max_length=200)  # Translate
    export_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)

    def natural_key(self):
        return [self.export_id]

    def __str__(self):
        return self.name


class TermTab(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    title = models.CharField(verbose_name="Title of this tab", max_length=100)  # Translate
    description = models.TextField()  # Translate

    def natural_key(self):
        return self.term.natural_key() + [self.title]

    def __str__(self):
        return self.title


class TermLink(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    url = models.CharField(verbose_name="URL", max_length=300)  # Translate
    link_text = models.CharField(verbose_name="Link text", max_length=80)  # Translate

    def natural_key(self):
        return self.term.natural_key() + [self.url]



# ^
# |
# TERMS
# CALENDAR
# |
# V


class Calendar(models.Model, ExportImportMixin):
    """A multi purpose calendar for course events markups, time reservations etc."""

    objects = SlugManager()

    name = models.CharField(
        verbose_name="Name for reference in content", max_length=200, unique=True
    )
    allow_multiple = models.BooleanField(verbose_name="Allow multiple reservation", default=False)
    related_content = models.ForeignKey(
        "ContentPage", on_delete=models.SET_NULL, null=True, blank=True
    )
    origin = models.ForeignKey(Course, verbose_name="Course", null=True, on_delete=models.SET_NULL)
    slug = models.SlugField(max_length=255, allow_unicode=True, blank=False)

    def natural_key(self):
        return [self.name]

    def save(self, *args, **kwargs):
        self.slug = get_prefixed_slug(self, self.origin, "name", translated=False)
        super().save(*args, **kwargs)


    def __str__(self):
        return self.name


class CalendarDate(models.Model):
    """A single date on a calendar."""

    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    event_name = models.CharField(verbose_name="Name of the event", max_length=200)  # Translate
    event_description = models.CharField(
        verbose_name="Description", max_length=200, blank=True, null=True
    )  # Translate
    start_time = models.DateTimeField(verbose_name="Starts at")
    end_time = models.DateTimeField(verbose_name="Ends at")
    reservable_slots = models.IntegerField(verbose_name="Amount of reservable slots")

    def __str__(self):
        return self.event_name

    def get_users(self):
        return self.calendarreservation_set.all().values_list("user")

    def duration(self):
        return self.end_time - self.start_time


class CalendarReservation(models.Model):
    """A single user-made reservation on a calendar date."""

    calendar_date = models.ForeignKey(CalendarDate, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)


# ^
# |
# CALENDAR
# CONTENT BASE
# |
# V

class EmbeddedLinkManager(models.Manager):

    def get_by_natural_key(self, instance_slug, parent_slug, content_slug):
        return self.get(
            instance__slug=instance_slug,
            parent__slug=parent_slug,
            embedded_page__slug=content_slug,
        )


class EmbeddedLink(models.Model, ExportImportMixin):
    objects = EmbeddedLinkManager()

    parent = models.ForeignKey("ContentPage", related_name="emb_parent", on_delete=models.CASCADE)
    embedded_page = models.ForeignKey(
        "ContentPage", related_name="emb_embedded", on_delete=models.RESTRICT
    )
    revision = models.PositiveIntegerField(blank=True, null=True)
    ordinal_number = models.PositiveSmallIntegerField()
    instance = models.ForeignKey("CourseInstance", on_delete=models.CASCADE)

    class Meta:
        ordering = ["ordinal_number"]

    def natural_key(self):
        return (self.instance.slug, self.parent.slug, self.embedded_page.slug)

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "embedded_page", freeze_to)

    def set_instance(self, instance):
        self.instance = instance


class ContentPage(models.Model, ExportImportMixin):
    """
    This class determines the base for all content in Lovelace. All pages that can be displayed
    as course content or embedded into other pages must be created as proxy models of this class.

    This class handles base behavior for all pages, consisting of
    - rendering markup
    - caching rendered markup
    - doing replace operations on markup
    - saving and handling evaluations
    - managing embedded links in the markup

    Content types must be registered after definition using the register_content_type class method.
    This class contains black sorcery that delegates certain method calls to child classes based
    on the content type attribute. See __getattribute__ for details.
    """

    class Meta:
        ordering = ("name",)
        unique_together = ("name", "origin")

    objects = SlugManager()

    # This will ideally be deprecated and replaced by a list generated dynamically from
    # registered content types.
    CONTENT_TYPE_CHOICES = (
        ("LECTURE", "Lecture"),
        ("TEXTFIELD_EXERCISE", "Textfield exercise"),
        ("MULTIPLE_CHOICE_EXERCISE", "Multiple choice exercise"),
        ("CHECKBOX_EXERCISE", "Checkbox exercise"),
        ("FILE_UPLOAD_EXERCISE", "File upload exercise"),
        ("REPEATED_TEMPLATE_EXERCISE", "Repeated template exercise"),
        ("ROUTINE_EXERCISE", "Routine exercise"),
        ("MULTIPLE_QUESTION_EXAM", "Multiple question exam"),
    )

    # Dynamically registered content types go here.
    content_type_models = {}

    # Template to use for rendering this content type, all content type models must set their own.
    template = "courses/blank.html"

    # Template for answers page for tasks of this type, override if the default is not suitable.
    answers_template = "courses/user-exercise-answers.html"
    answers_show_log = False

    # Classes to include for the answers table. Override if needed.
    answer_table_classes ="fixed alternate-green answers-table"


    # Model fields that are shared by all content types.
    # v
    name = models.CharField(max_length=255, help_text="The full name of this page")  # Translate
    origin = models.ForeignKey(
        Course, verbose_name="Origin course", null=True, on_delete=models.SET_NULL
    )
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )
    content = models.TextField(
        verbose_name="Page content body", blank=True, default=""
    )  # Translate
    default_points = models.IntegerField(
        default=1,
        help_text="The default points a user can gain by finishing this exercise correctly",
    )
    access_count = models.PositiveIntegerField(editable=False, default=0)
    tags = ArrayField(
        base_field=models.CharField(max_length=32, blank=True),
        default=list,
        blank=True,
    )
    evaluation_group = models.CharField(
        max_length=32,
        help_text="Evaluation group identifier for binding together mutually exclusive tasks.",
        blank=True,
    )
    content_type = models.CharField(max_length=28, default="LECTURE", choices=CONTENT_TYPE_CHOICES)
    embedded_pages = models.ManyToManyField(
        "self",
        blank=True,
        through=EmbeddedLink,
        symmetrical=False,
        through_fields=("parent", "embedded_page", "instance"),
    )
    feedback_questions = models.ManyToManyField(feedback.models.ContentFeedbackQuestion, blank=True)

    question = models.TextField(blank=True, default="")  # Translate
    manually_evaluated = models.BooleanField(
        verbose_name="This exercise is evaluated by hand", default=False
    )
    delayed_evaluation = models.BooleanField(
        verbose_name="This exercise is not immediately evaluated", default=False
    )
    answer_limit = models.PositiveSmallIntegerField(
        verbose_name="Limit number of allowed attempts to", blank=True, null=True
    )
    group_submission = models.BooleanField(
        verbose_name="Answers can be submitted as a group", default=False
    )
    ask_collaborators = models.BooleanField(
        verbose_name="Ask the student to list collaborators", default=False
    )
    # ^

    @classmethod
    def register_content_type(cls, constant_name, type_class, answer_class=None):
        if not issubclass(type_class, cls):
            raise TypeError(
                _("Class {type_class} is not a subclass of {cls}").format(
                    type_class=type_class,
                    cls=cls
                )
            )

        cls.content_type_models[constant_name] = type_class

    def natural_key(self):
        return (self.slug, )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super().save(*args, **kwargs)

    def replace_lines(self, line_idx, new_lines, delete_count=1):
        """
        Replaces one or more lines in the page's markup, in the content field of the currently
        active language. If currently active language is empty, changes the default language
        content field instead.

        Always use this method to edit markup when creating content editing tools. The calling
        end is expected to know how many lines are being replaced. This information is available
        as the content data's block size value.
        """

        lang = translation.get_language()
        if not getattr(self, f"content_{lang}"):
            field = f"content_{settings.MODELTRANSLATION_DEFAULT_LANGUAGE}"
        else:
            field = f"content_{lang}"

        lines = getattr(self, field).splitlines()
        del lines[line_idx:line_idx + delete_count]
        for i, line in enumerate(new_lines):
            lines.insert(line_idx + i, line)

        setattr(self, field, "\n".join(lines))
        self.save()

    def rendered_markup(self, request=None, context=None, revision=None, lang_code=None, page=None):
        """
        Uses the included MarkupParser library to render the page content into
        a data format that can be used by templates and safely cached. If a rendered version
        already exists in the cache, use that instead. If page breaks are used, creates both
        paginated and full versions of the content, but only returns the requested markup (either
        1 page or full content).

        This version of rendering is only used for top-level pages.
        """

        # This import needs to be here until circular import issues are fully sorted out.
        from courses import markupparser

        parser = markupparser.MarkupParser()

        blocks = []
        embedded_pages = []
        instance = context["instance"]

        if lang_code is None:
            lang_code = translation.get_language()

        # Check cache
        if page is not None:
            cached_content = cache.get(f"{self.slug}_contents_{instance.slug}_{lang_code}_{page}")
        else:
            cached_content = cache.get(f"{self.slug}_contents_{instance.slug}_{lang_code}")

        if cached_content is None:
            if revision is None:
                content = self.content
            else:
                content = get_single_archived(self, revision).content

            # Render the page
            context["content"] = self
            context["lang_code"] = lang_code
            markup_gen = parser.parse(content, request, context, embedded_pages)
            segment = ""
            pages = []
            for chunk in markup_gen:
                if isinstance(chunk, markupparser.PageBreak):
                    pages.append(blocks)
                    blocks = []
                else:
                    blocks.append(chunk)

            pages.append(blocks)

            if len(pages) > 1:
                for i, blocks in enumerate(pages, start=1):
                    cache.set(
                        f"{self.slug}_contents_{instance.slug}_{lang_code}_{i}",
                        blocks,
                        timeout=None,
                    )

            full = [block for page in pages for block in page]
            cache.set(
                f"{self.slug}_contents_{instance.slug}_{lang_code}",
                full,
                timeout=None,
            )

            if page is not None:
                return pages[page - 1]
            return full

        return cached_content

    def _get_rendered_content(self, context):
        """
        This method renders markup for embedded pages. It is called from within the markup parser
        when it encounters an embedded page. Child models are expected to have a public version of
        this method get_rendered_content, and it is expected to call this method first, then
        provide its additions to the rendered markup as needed.

        See routine exercise or multiexam content types for examples of tasks that have their
        own includes to the rendered content. As extra content is not editable, it should always
        be a content block that has the 'extra' type, line index of -1, and line count of 0.
        e.g. ["extra", "rendered content string", -1, 0]
        """

        from courses import markupparser

        embedded_content = []
        parser = markupparser.MarkupParser()
        markup_gen = parser.parse(self.content, context=context)
        for chunk in markup_gen:
            try:
                embedded_content.append(chunk)
            except ValueError as e:
                raise markupparser.EmbeddedObjectNotAllowedError(
                    "embedded pages are not allowed inside embedded pages"
                )
        return embedded_content

    def _get_question(self, context):
        """
        This method is for rendering the questions box of a task. Similarly to _get_rendered_content
        it is called from within the markup parser as it encounters embedded pages. Also similarly,
        child models are expected to have the public version of this method that calls this method,
        and then makes its own additions to the question box as needed.
        """

        from courses import blockparser

        question = blockparser.parseblock(escape(self.question, quote=False), context)
        return question

    def count_pages(self, instance):
        """
        Counts the number of pages the content has been paginated to. Uses cache keys to avoid
        needing to read the content for page breaks.
        """

        lang_code = translation.get_language()
        content_key = f"{self.slug}_contents_{instance.slug}_{lang_code}"
        keys = cache.keys(content_key + "*")

        # Return -1 because the full page is cached separately.
        return len(keys) - 1

    # NOTE: This method was separated from the normal parsing of markup for legacy reasons
    #       Because the this only needs to be done when the content has changed whereas
    #       before caching, the content rendering was done much more frequently.
    #       Presently only manual cache regen renders the content without a need to run this
    #       process, so there is sufficient basis for combining this into the rendering process.
    def update_embedded_links(self, instance, revision=None):
        """
        Uses LinkMarkupParser to discover all embedded page links
        within the page content and creates EmbeddedLink and CourseMediaLink
        objects based on links found in the markup.
        """
        from courses import markupparser

        page_links = set()
        media_links = set()

        page_links_per_lang = {}

        parser = markupparser.LinkParser()
        for lang_code, _ in settings.LANGUAGES:
            if revision is None:
                content = getattr(self, f"content_{lang_code}")
            else:
                version = Version.objects.get_for_object(self).get(revision_id=revision).field_dict
                content = version[f"content_{lang_code}"]

            lang_page_links, lang_media_links = parser.parse(content, instance)
            page_links = page_links.union(lang_page_links)
            media_links = media_links.union(lang_media_links)
            page_links_per_lang[lang_code] = lang_page_links

        old_page_links = list(
            EmbeddedLink.objects.filter(instance=instance, parent=self).values_list(
                "embedded_page__slug", flat=True
            )
        )
        old_media_links = list(
            CourseMediaLink.objects.filter(instance=instance, parent=self).values_list(
                "media__name", flat=True
            )
        )

        removed_page_links = set(old_page_links).difference(page_links)
        removed_media_links = set(old_media_links).difference(media_links)
        added_page_links = set(page_links).difference(old_page_links)
        added_media_links = set(media_links).difference(old_media_links)

        EmbeddedLink.objects.filter(
            embedded_page__slug__in=removed_page_links, instance=instance, parent=self
        ).delete()
        CourseMediaLink.objects.filter(
            media__name__in=removed_media_links, instance=instance, parent=self
        ).delete()

        # set ordinal to zero at first, updated per language later
        for link_slug in added_page_links:
            link_obj = EmbeddedLink(
                parent=self,
                embedded_page=ContentPage.objects.get(slug=link_slug),
                revision=None,
                ordinal_number=0,
                instance=instance,
            )
            link_obj.save()

        for link_slug in added_media_links:
            link_obj = CourseMediaLink(
                parent=self,
                media=CourseMedia.objects.get(name=link_slug),
                instance=instance,
                revision=None,
            )
            link_obj.save()

        for lang_code, _ in settings.LANGUAGES:
            for i, link_slug in enumerate(page_links_per_lang[lang_code]):
                link_obj = EmbeddedLink.objects.get(
                    embedded_page__slug=link_slug, instance=instance, parent=self
                )
                link_obj.ordinal_number = i
                link_obj.save()
                link_obj.embedded_page.update_embedded_links(instance)

    def regenerate_cache(self, instance, active_only=False):
        """
        Forcibly regenerates content page's cache for the given course instance. If active_only
        is set to true, the process will be skipped if the page is archived.
        """

        context = {"instance": instance, "course": instance.course, "content_page": self}
        try:
            revision = ContentGraph.objects.get(content=self, instance=instance).revision
        except ContentGraph.DoesNotExist:
            return

        if active_only and revision is not None:
            return

        current_lang = translation.get_language()

        for lang_code, _ in settings.LANGUAGES:
            translation.activate(lang_code)
            content_key = f"{self.slug}_contents_{instance.slug}_{lang_code}"
            for key in cache.keys(content_key + "*"):
                cache.delete(key)

            self.rendered_markup(instance, context, lang_code=lang_code, revision=revision)
        translation.activate(current_lang)

        from faq.utils import regenerate_cache
        regenerate_cache(instance, self)

    def get_human_readable_type(self):
        humanized_type = self.content_type.replace("_", " ").lower()
        return humanized_type

    def get_dashed_type(self):
        dashed_type = self.content_type.replace("_", "-").lower()
        return dashed_type

    def get_admin_change_url(self):
        """
        Forms change URL to modify this content from the management panel. Because
        app name is part of the URL, this method needs to be overridden in all child
        models that are defined in separate apps.
        """

        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:courses_{adminized_type}_change", args=(self.id,))

    def get_staff_extra(self, context):
        """
        Overriding this method allows content types to include additional staff tools in the
        left hand context menu. This method needs to return a list with (link text, link url)
        tuples as its values.
        """

        return []

    def get_url_name(self):
        return get_prefixed_slug(self, self.origin, "name")

    def is_answerable(self):
        return self.content_type != "LECTURE"

    def save_evaluation(self, user, evaluation, answer_object):
        """
        Saves evaluation. This method has been designed in a way that it is generally compatible
        with all task types as it simply saves an evaluation that has been generated by the task
        itself.

        This method also takes care of updating completion, and updating the evaluation for
        group members when applicable, and making a copy of the answer for each of them.

        Evaluation dictionary and its default values are defined as follows:
        - *evaluation: bool
        - points: float (0)
        - max: float (exercise.default_points)
        - manual: bool (False)
        - evaluator: User (None)
        - test_results: string ("")
        - feedback: string ("")
        """

        from utils.exercise import update_completion
        from utils.users import get_group_members

        instance = answer_object.instance
        correct = evaluation["evaluation"]
        if correct and not evaluation.get("manual", False):
            if "points" in evaluation:
                points = evaluation["points"]
            else:
                points = self.default_points
                evaluation["points"] = points
        else:
            points = 0

        evaluation_object = Evaluation(
            correct=correct,
            points=points,
            max_points=evaluation.get("max", self.default_points),
            evaluator=evaluation.get("evaluator"),
            test_results=evaluation.get("test_results", ""),
            feedback=evaluation.get("feedback", ""),
        )
        evaluation_object.save()
        answer_object.evaluation = evaluation_object
        answer_object.save()

        answer_object.refresh_from_db()

        update_completion(self, instance, user, evaluation, answer_object.answer_date)
        if self.group_submission:
            for member in get_group_members(user, instance):
                answer_object.pk = None
                answer_object.useranswer_ptr = None
                answer_object.user = member
                answer_object.save()
                update_completion(self, instance, member, evaluation, answer_object.answer_date)

        return evaluation_object

    def update_evaluation(self, user, evaluation, answer_object, complete=True, overwrite=False):
        """
        Updates an existing evaluation based on a new evaluation dictionary. See save_evaluation.
        This is used by tasks that use manual assesssment, or delayed evaluation.
        As default behavior completion is only updated if the new evaluation is better than the
        existing one. This can be overridden by settings overwrite to True.
        """

        from utils.exercise import update_completion
        from utils.users import get_group_members

        instance = answer_object.instance
        answer_object.evaluation.correct = evaluation["evaluation"]
        answer_object.evaluation.points = evaluation["points"]
        answer_object.evaluation.max_points = evaluation.get("max", self.default_points)
        answer_object.evaluation.feedback = evaluation.get("feedback", "")
        answer_object.evaluation.evaluator = evaluation.get("evaluator", None)
        answer_object.evaluation.test_results = evaluation.get("test_results", "")
        answer_object.evaluation.suspect = evaluation.get("suspect", False)
        answer_object.evaluation.comment = evaluation.get("comment", "")
        answer_object.evaluation.save()
        if complete:
            update_completion(
                self, instance, user, evaluation, answer_object.answer_date,
                overwrite=overwrite
            )
            if self.group_submission:
                for member in get_group_members(user, instance):
                    update_completion(
                        self, instance, member, evaluation, answer_object.answer_date,
                        overwrite=overwrite
                    )

    def get_user_evaluation(self, user, instance, check_group=True):
        """
        Gets a user's evaluation for this content. In the present day it only serves as a proxy to
        get the completion state.
        """

        try:
            completion = UserTaskCompletion.objects.get(user=user, instance=instance, exercise=self)
            return completion.state, completion.points
        except UserTaskCompletion.DoesNotExist:
            return "unanswered", 0

    def re_evaluate(self, user, instance):
        """
        Re-evaluates a task by picking the user's best result, and updating completion based on it.
        This method is primarily used when transfering records between instances that have different
        scoring rules.
        """

        from utils.exercise import update_completion

        best_answer = (
            self.get_user_answers(self, user, instance)
            .filter(evaluation__correct=True)
            .order_by("-evaluation__points")
            .first()
        )
        if not best_answer:
            return

        evaluation = {
            "evaluation": True,
            "points": best_answer.evaluation.points,
            "max": self.default_points,
        }
        update_completion(self, instance, user, evaluation, best_answer.answer_date)


    # Abstract methods that proxy model classes need to implement.
    # v

    def get_user_answers(self, user, instance, ignore_drafts=True):
        """
        Method that all task content types need to implement. Should return a queryset.
        """
        raise NotImplementedError("base type has no method 'get_user_answers'")


    def get_choices(self, revision=None):
        """
        Method that all task content types need to implement. Should return an iterable, or
        None if not applicable to the task type. The name says 'choices' for legacy reasons but it
        also includes things like textfield task answers.
        """
        raise NotImplementedError("base type has no method 'get_choices'")

    def save_answer(self, user, ip, answer, files, instance, revision):
        """
        Method that all task content types need to implement if they use the standard check_answer
        view for processing answers (generally recommended unless behavior needs to be entirely
        different, e.g. routine exercise). The saved answer should be a child model of UserAnswer.

        :param User user: instance of User
        :param str ip: IP address the answer was sent from (saved to the answer model instance)
        :param querydict answer: has the contents of the answer form as a Django querydict
        :param dict files: a dictionary-like object that contains UploadedFile instances
        :param CourseInstance instance: context where the answer was given
        :param int revision: revision the answer was submitted for

        :return: the created answer object (instance of UserAnswer child class)
        """
        raise NotImplementedError("base type has no method 'save_answer'")

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        """
        A follow-up method for save_answer, similarly mandatory if using standard views. This
        function checks the answer and return an evaluation dictionary that should conform to the
        format shown in save_evaluation docstring. When using standard views it should not save
        the evaluation.

        :param User user: instance of User
        :param str ip: IP address the answer was sent from (saved to the answer model instance)
        :param querydict answer: has the contents of the answer form as a Django querydict
        :param dict files: a dictionary-like object that contains UploadedFile instances
        :param UserAnswer answer_object: saved instance of UserAnswer child class
        :param int revision: revision the answer was submitted for

        :return: evaluation as dictionary
        """
        raise NotImplementedError("base type has no method 'save_answer'")

    # ^


    def get_feedback_questions(self):
        return [q.get_type_object() for q in self.feedback_questions.all()]

    def __str__(self):
        return self.name

    # Everything past here is part of the machinations that allow content to be referenced
    # as a common type and handled as if they were the same, and also have their own behaviors
    # at the same time. This whole mechanism needs to be revised but proxy models aren't making
    # it easy.
    # v

    def get_type_object(self):
        # this seems to lose the revision info?
        from routine_exercise.models import RoutineExercise
        from multiexam.models import MultipleQuestionExam

        type_models = {
            "LECTURE": Lecture,
            "TEXTFIELD_EXERCISE": TextfieldExercise,
            "MULTIPLE_CHOICE_EXERCISE": MultipleChoiceExercise,
            "CHECKBOX_EXERCISE": CheckboxExercise,
            "FILE_UPLOAD_EXERCISE": FileUploadExercise,
            "REPEATED_TEMPLATE_EXERCISE": RepeatedTemplateExercise,
            "ROUTINE_EXERCISE": RoutineExercise,
            "MULTIPLE_QUESTION_EXAM": MultipleQuestionExam,
        }

        return type_models[self.content_type].objects.get(id=self.id)

    def get_type_model(self):
        from routine_exercise.models import RoutineExercise
        from multiexam.models import MultipleQuestionExam

        type_models = {
            "LECTURE": Lecture,
            "TEXTFIELD_EXERCISE": TextfieldExercise,
            "MULTIPLE_CHOICE_EXERCISE": MultipleChoiceExercise,
            "CHECKBOX_EXERCISE": CheckboxExercise,
            "FILE_UPLOAD_EXERCISE": FileUploadExercise,
            "REPEATED_TEMPLATE_EXERCISE": RepeatedTemplateExercise,
            "ROUTINE_EXERCISE": RoutineExercise,
            "MULTIPLE_QUESTION_EXAM": MultipleQuestionExam,
        }
        return type_models[self.content_type]

    def get_answer_model(self):
        from routine_exercise.models import RoutineExerciseAnswer
        from multiexam.models import UserMultipleQuestionExamAnswer

        answer_models = {
            "LECTURE": None,
            "TEXTFIELD_EXERCISE": UserTextfieldExerciseAnswer,
            "MULTIPLE_CHOICE_EXERCISE": UserMultipleChoiceExerciseAnswer,
            "CHECKBOX_EXERCISE": UserCheckboxExerciseAnswer,
            "FILE_UPLOAD_EXERCISE": UserFileUploadExerciseAnswer,
            "REPEATED_TEMPLATE_EXERCISE": UserRepeatedTemplateExerciseAnswer,
            "ROUTINE_EXERCISE": RoutineExerciseAnswer,
            "MULTIPLE_QUESTION_EXAM": UserMultipleQuestionExamAnswer,
        }
        return answer_models[self.content_type]

    # HACK: Experimental way of implementing a better get_type_object
    def __getattribute__(self, name):
        """
        Defines when attribute access needs to be delegated to a child model. Note that
        this results in methods being returned as functions, so they must be called with the
        model instance as the first argument.
        """

        normal = [
            "get_choices",
            "get_rendered_content",
            "get_question",
            "save_answer",
            "check_answer",
            "get_user_answers",
            "get_staff_extra",
            "template",
            "answers_template",
            "answer_table_classes",
            "answers_show_log",
            "export",
        ]

        if name in normal:
            type_model = self.get_type_model()
            type_attr = getattr(type_model, name)
        elif name == "get_admin_change_url":
            type_model = self.get_type_model()
            # Can be called from a template (without parameter)
            type_attr = lambda: type_model.get_admin_change_url(self)
        else:
            return super().__getattribute__(name)
        return type_attr

    # ^

# ^
# |
# CONTENT BASE
# CONTENT TYPES
# |
# V


class Lecture(ContentPage):
    """A single page for a lecture."""

    class Meta:
        verbose_name = "lecture page"
        proxy = True

    template = "courses/lecture.html"

    def get_choices(self, revision=None):
        pass

    def get_rendered_content(self, context):
        return ContentPage._get_rendered_content(self, context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "LECTURE"
        super().save(*args, **kwargs)

    def get_user_evaluation(self, user, instance, check_group=True):
        pass

    def get_user_answers(self, user, instance, ignore_drafts=True):
        raise NotImplementedError


class MultipleChoiceExercise(ContentPage):
    class Meta:
        verbose_name = "multiple choice exercise"
        proxy = True

    template = "courses/multiple-choice-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "MULTIPLE_CHOICE_EXERCISE"
        super().save(*args, **kwargs)

    def get_choices(self, revision=None):
        if revision is None:
            choices = self.multiplechoiceexerciseanswer_set.get_queryset().order_by("ordinal")
        else:
            choices = get_archived_field(self, revision, "multiplechoiceexerciseanswer_set")
            choices.sort(key=lambda c: c.ordinal or c.id)
        return choices

    def get_rendered_content(self, context):
        return ContentPage._get_rendered_content(self, context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def save_answer(self, user, ip, answer, files, instance, revision):
        keys = list(answer.keys())
        key = [k for k in keys if k.endswith("-radio")]
        if not key:
            raise InvalidExerciseAnswerException("No answer was picked!")
        answered = int(answer[key[0]])

        try:
            chosen_answer = MultipleChoiceExerciseAnswer.objects.get(id=answered)
        except MultipleChoiceExerciseAnswer.DoesNotExist as e:
            raise InvalidExerciseAnswerException("The received answer does not exist!") from e

        answer_object = UserMultipleChoiceExerciseAnswer(
            exercise_id=self.id,
            chosen_answer=chosen_answer,
            user=user,
            answerer_ip=ip,
            instance=instance,
            revision=revision,
        )
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        choices = self.get_choices(self, revision)

        # quick hax:
        answered = int([v for k, v in answer.items() if k.endswith("-radio")][0])

        # Determine, if the given answer was correct and which hints to show
        correct = False
        hints = []
        comments = []
        for choice in choices:
            if answered == choice.id and choice.correct:
                correct = True
                if choice.comment:
                    comments.append(choice.comment)
            elif answered != choice.id and choice.correct:
                if choice.hint:
                    hints.append(choice.hint)
            elif answered == choice.id and not choice.correct:
                if choice.hint:
                    hints.append(choice.hint)
                if choice.comment:
                    comments.append(choice.comment)

        return {
            "evaluation": correct,
            "hints": hints,
            "comments": comments,
            "points": correct * self.default_points,
        }

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserMultipleChoiceExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserMultipleChoiceExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers

    def export(self, instance, export_target):
        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_many_python(self.get_choices(self)),
            f"{self.slug}_choices",
            export_target,
        )


# @reversion.register(follow=["checkboxexerciseanswer_set"])
class CheckboxExercise(ContentPage):
    class Meta:
        verbose_name = "checkbox exercise"
        proxy = True

    template = "courses/checkbox-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "CHECKBOX_EXERCISE"
        super().save(*args, **kwargs)

    def get_choices(self, revision=None):
        if revision is None:
            choices = self.checkboxexerciseanswer_set.get_queryset().order_by("ordinal")
        else:
            choices = get_archived_field(self, revision, "checkboxexerciseanswer_set")
            choices.sort(key=lambda c: c.ordinal or c.id)
        return choices

    def get_rendered_content(self, context):
        return ContentPage._get_rendered_content(self, context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def save_answer(self, user, ip, answer, files, instance, revision):
        chosen_answer_ids = [int(i) for i, _ in answer.items() if i.isdigit()]

        chosen_answers = CheckboxExerciseAnswer.objects.filter(
            id__in=chosen_answer_ids
        ).values_list("id", flat=True)
        if set(chosen_answer_ids) != set(chosen_answers):
            raise InvalidExerciseAnswerException("One or more of the answers do not exist!")

        answer_object = UserCheckboxExerciseAnswer(
            exercise_id=self.id,
            user=user,
            answerer_ip=ip,
            instance=instance,
            revision=revision,
        )
        answer_object.save()
        answer_object.chosen_answers.add(*chosen_answers)
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        # Determine, if the given answer was correct and which hints to show

        choices = self.get_choices(self, revision)

        # quick hax:
        answered = {choice.id: False for choice in choices}
        answered.update({int(i): True for i, _ in answer.items() if i.isdigit()})

        correct = True
        hints = []
        comments = []
        chosen = []
        for choice in choices:
            if answered[choice.id] and choice.correct and correct:
                correct = True
                chosen.append(choice)
                if choice.comment:
                    comments.append(choice.comment)
            elif not answered[choice.id] and choice.correct:
                correct = False
                if choice.hint:
                    hints.append(choice.hint)
            elif answered[choice.id] and not choice.correct:
                correct = False
                if choice.hint:
                    hints.append(choice.hint)
                if choice.comment:
                    comments.append(choice.comment)
                chosen.append(choice)

        return {
            "evaluation": correct,
            "hints": hints,
            "comments": comments,
            "points": correct * self.default_points,
        }

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserCheckboxExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserCheckboxExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers

    def export(self, instance, export_target):
        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_many_python(self.get_choices(self)),
            f"{self.slug}_choices",
            export_target,
        )


class TextfieldExercise(ContentPage):
    class Meta:
        verbose_name = "text field exercise"
        proxy = True

    template = "courses/textfield-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "TEXTFIELD_EXERCISE"
        super().save(*args, **kwargs)

    def get_choices(self, revision=None):
        if revision is None:
            choices = self.textfieldexerciseanswer_set.get_queryset()
        else:
            choices = get_archived_field(self, revision, "textfieldexerciseanswer_set")
        return choices

    def get_rendered_content(self, context):
        return ContentPage._get_rendered_content(self, context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def save_answer(self, user, ip, answer, files, instance, revision):
        if "answer" in answer.keys():
            given_answer = answer["answer"].replace("\r", "")
        else:
            raise InvalidExerciseAnswerException("Answer missing!")

        answer_object = UserTextfieldExerciseAnswer(
            exercise_id=self.id,
            given_answer=given_answer,
            user=user,
            answerer_ip=ip,
            instance=instance,
            revision=revision,
        )
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, user_answer, files, answer_object, revision):
        answers = self.get_choices(self, revision)

        # Determine, if the given answer was correct and which hints/comments to show
        correct = False
        hints = []
        comments = []
        errors = []

        if "answer" in user_answer.keys():
            given_answer = user_answer["answer"].replace("\r", "")
        else:
            return {"evaluation": False}

        def re_validate(db_ans, given_ans):
            m = re.match(db_ans, given_ans)
            return (m is not None, m)

        def str_validate(db_ans, given_ans):
            return (db_ans == given_ans, None)

        for answer in answers:
            validate = re_validate if answer.regexp else str_validate

            try:
                match, m = validate(answer.answer, given_answer)
            except re.error as e:
                if user.is_staff:
                    errors.append(f"Contact staff, regexp error '{e}' from regexp: {answer.answer}")
                else:
                    errors.append(f"Contact staff! Regexp error '{e}' in exercise '{self.name}'.")
                if answer.correct:
                    correct = False
                continue

            sub = lambda text: text
            if m is not None and m.groupdict():
                groups = {
                    re.escape(f"{{{k}}}"): v for k, v in m.groupdict().items() if v is not None
                }
                if groups:
                    pattern = re.compile(
                        "|".join((re.escape(f"{{{k}}}") for k in m.groupdict().keys()))
                    )
                    sub = lambda text: pattern.sub(lambda mo: groups[re.escape(mo.group(0))], text)

            hint = comment = ""
            if answer.hint:
                hint = sub(answer.hint)
            if answer.comment:
                comment = sub(answer.comment)

            if match and answer.correct:
                correct = True
                if comment:
                    comments.append(comment)
            elif match and not answer.correct:
                if hint:
                    hints.append(hint)
                if comment:
                    comments.append(comment)
            elif not match and answer.correct:
                if hint:
                    hints.append(hint)

        return {
            "evaluation": correct,
            "hints": hints,
            "comments": comments,
            "errors": errors,
            "points": correct * self.default_points
        }

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserTextfieldExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserTextfieldExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers

    def export(self, instance, export_target):
        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_many_python(self.get_choices(self)),
            f"{self.slug}_choices",
            export_target,
        )


class FileUploadExercise(ContentPage):
    class Meta:
        verbose_name = "file upload exercise"
        proxy = True

    template = "courses/file-upload-exercise.html"
    answers_show_log = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)


        self.content_type = "FILE_UPLOAD_EXERCISE"

        super().save(*args, **kwargs)
        # create the extra settings model instance if one doesn't exist yet
        if not hasattr(self, "fileexercisesettings"):
            print("Creating settings")
            extra_settings = FileExerciseSettings(exercise=self)
            extra_settings.save()

        parents = ContentPage.objects.filter(embedded_pages=self).distinct()
        for instance in CourseInstance.objects.filter(
            Q(contentgraph__content=self) | Q(contentgraph__content__embedded_pages=self),
            frozen=False,
        ).distinct():
            self.update_embedded_links(instance)
            for parent in parents:
                parent.regenerate_cache(instance)

    def save_answer(self, user, ip, answer, files, instance, revision):
        answer_object = UserFileUploadExerciseAnswer(
            exercise_id=self.id,
            user=user,
            answerer_ip=ip,
            instance=instance,
            revision=revision,
        )
        answer_object.save()

        if files:
            filelist = files.getlist("file")
            for uploaded_file in filelist:
                if self.fileexercisesettings.allowed_filenames not in ([], [""]):
                    for fnpat in self.fileexercisesettings.allowed_filenames:
                        if fnmatch(uploaded_file.name, fnpat):
                            break
                    else:
                        raise InvalidExerciseAnswerException(
                            _(
                                "Filename {} is not listed in accepted filenames. Allowed:\n{}"
                            ).format(uploaded_file.name, ", ".join(
                                self.fileexercisesettings.allowed_filenames)
                            )
                        )

                return_file = FileUploadExerciseReturnFile(
                    answer=answer_object, fileinfo=uploaded_file
                )
                return_file.save()
        elif self.fileexercisesettings.answer_mode == "TEXT":
            if not self.fileexercisesettings.answer_filename:
                raise InvalidExerciseAnswerException(
                    _("Task improperly configured, notify staff!")
                )

            if "answer" in answer.keys():
                given_answer = bytes(answer["answer"].replace("\r", ""), encoding="utf-8")
            else:
                raise InvalidExerciseAnswerException("Answer missing!")

            uploaded_file = ContentFile(given_answer)
            return_file = FileUploadExerciseReturnFile(answer=answer_object)
            return_file.fileinfo.save(self.fileexercisesettings.answer_filename, uploaded_file)
            return_file.save()
        else:
            raise InvalidExerciseAnswerException("No file was sent!")
        return answer_object

    def get_choices(self, revision=None):
        return

    def get_rendered_content(self, context):
        return ContentPage._get_rendered_content(self, context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def get_admin_change_url(self):
        return reverse("exercise_admin:file_upload_change", args=(self.id,))

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        import courses.tasks as rpc_tasks
        from utils.exercise import file_upload_payload

        if revision == "head":
            revision = None

        if self.fileexercisetest_set.get_queryset():
            filelist = files.getlist("file")
            if not filelist and self.fileexercisesettings.answer_filename:
                filelist.append(ContentFile(
                    bytes(answer["answer"].replace("\r", ""), encoding="utf-8"),
                    name=self.fileexercisesettings.answer_filename
                ))

            payload = file_upload_payload(self, filelist, answer_object.instance, revision)

            result = rpc_tasks.run_tests.delay(payload=payload)
            answer_object.task_id = result.task_id
            answer_object.save()
            return {"task_id": result.task_id}
        return {"evaluation": True, "manual": self.manually_evaluated}

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserFileUploadExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserFileUploadExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers

    def export(self, instance, export_target):
        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_single_python(self.fileexercisesettings),
            f"{self.slug}_settings",
            export_target,
        )
        for testfile in self.fileexercisetestincludefile_set.get_queryset():
            testfile.export(instance, export_target)
        for test in self.fileexercisetest_set.get_queryset():
            test.export(instance, export_target)
        for ifile_link in self.instanceincludefiletoexerciselink_set.get_queryset():
            ifile_link.export(instance, export_target)


# Legacy task type only kept for compatibility, use routine exercise instead
class RepeatedTemplateExercise(ContentPage):
    class Meta:
        verbose_name = "repeated template exercise"
        proxy = True

    template = "courses/repeated-template-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "REPEATED_TEMPLATE_EXERCISE"
        RepeatedTemplateExerciseSession.objects.filter(exercise=self, user=None).delete()
        super().save(*args, **kwargs)

    def get_choices(self, revision=None):
        return

    def get_rendered_content(self, context):
        content = ContentPage._get_rendered_content(self, context)
        t = loader.get_template("courses/repeated-template-content-extra.html")
        return content + [("extra", t.render(context), -1, 0)]

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserRepeatedTemplateExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserRepeatedTemplateExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers

    def save_answer(self, user, ip, user_answer, files, instance, revision):
        if "answer" in user_answer.keys():
            given_answer = user_answer["answer"].replace("\r", "")
        else:
            raise InvalidExerciseAnswerException("Answer missing!")

        lang_code = translation.get_language()

        open_sessions = RepeatedTemplateExerciseSession.objects.filter(
            exercise_id=self.id,
            user=user,
            language_code=lang_code,
            repeatedtemplateexercisesessioninstance__userrepeatedtemplateinstanceanswer__isnull=True,
        )

        session = (
            open_sessions.exclude(
                repeatedtemplateexercisesessioninstance__userrepeatedtemplateinstanceanswer__correct=False
            )
            .distinct()
            .first()
        )

        session_instance = (
            RepeatedTemplateExerciseSessionInstance.objects.filter(
                session=session, userrepeatedtemplateinstanceanswer__isnull=True
            )
            .order_by("ordinal_number")
            .first()
        )

        if session is None or session_instance is None:
            raise InvalidExerciseAnswerException("Answering without a started session!")

        try:
            answer_object = UserRepeatedTemplateExerciseAnswer.objects.get(
                exercise_id=self.id, session=session
            )
        except UserRepeatedTemplateExerciseAnswer.DoesNotExist as e:
            answer_object = UserRepeatedTemplateExerciseAnswer(
                exercise_id=self.id,
                session=session,
                user=user,
                answerer_ip=ip,
                instance=instance,
                revision=revision,
            )
            answer_object.save()

        if not (
            UserRepeatedTemplateInstanceAnswer.objects.filter(
                session_instance=session_instance
            ).exists()
        ):
            instance_answer = UserRepeatedTemplateInstanceAnswer(
                answer=answer_object,
                session_instance=session_instance,
                given_answer=given_answer,
            )
            instance_answer.save()

        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        session = answer_object.session
        session_instance = (
            RepeatedTemplateExerciseSessionInstance.objects.filter(
                session=session, userrepeatedtemplateinstanceanswer__isnull=False
            )
            .order_by("ordinal_number")
            .last()
        )

        answers = RepeatedTemplateExerciseSessionInstanceAnswer.objects.filter(
            session_instance=session_instance
        )

        # Copied from textfield exercise

        # Determine, if the given answer was correct and which hints/comments to show
        correct = False
        hints = []
        comments = []
        triggers = []
        errors = []

        if "answer" in answer.keys():
            given_answer = answer["answer"].replace("\r", "")
        else:
            return {"evaluation": False}

        def re_validate(db_ans, given_ans):
            m = re.match(db_ans, given_ans)
            return (m is not None, m)

        def str_validate(db_ans, given_ans):
            return (db_ans == given_ans, None)

        for answer in answers:
            validate = re_validate if answer.regexp else str_validate

            try:
                match, m = validate(answer.answer, given_answer)
            except re.error as e:
                if user.is_staff:
                    errors.append(f"Regexp error '{e}' from regexp: {answer.answer}")
                else:
                    errors.append(f"Contact staff! Regexp error '{e}' in exercise '{self.name}'.")
                correct = False
                continue

            sub = lambda text: text
            if m is not None and m.groupdict():
                groups = {
                    re.escape(f"{{{k}}}"): v for k, v in m.groupdict().items() if v is not None
                }
                if groups:
                    pattern = re.compile(
                        "|".join((re.escape(f"{{{k}}}") for k in m.groupdict().keys()))
                    )
                    sub = lambda text: pattern.sub(lambda mo: groups[re.escape(mo.group(0))], text)

            hint = comment = ""
            if answer.hint:
                hint = sub(answer.hint)
            if answer.comment:
                comment = sub(answer.comment)

            if match and answer.correct:
                correct = True
                if comment:
                    comments.append(comment)
            elif match and not answer.correct:
                if hint:
                    hints.append(hint)
                if comment:
                    comments.append(comment)
            elif not match and answer.correct:
                if hint:
                    hints.append(hint)

        instance_answer = UserRepeatedTemplateInstanceAnswer.objects.get(
            session_instance=session_instance
        )
        instance_answer.correct = correct
        instance_answer.save()

        total_instances = session.total_instances()
        # +2: zero-indexing and next from current

        if correct:
            next_instance = (
                session_instance.ordinal_number + 2
                if session_instance.ordinal_number + 1 < total_instances
                else None
            )
        else:
            next_instance = None

        return {
            "evaluation": correct,
            "hints": hints,
            "comments": comments,
            "errors": errors,
            "triggers": triggers,
            "next_instance": next_instance,
            "total_instances": total_instances,
            "points": correct * self.default_points
        }

    def save_evaluation(self, user, evaluation, answer_object):
        session = answer_object.session
        instance_answers = UserRepeatedTemplateInstanceAnswer.objects.filter(
            answer__session=session
        )

        if instance_answers.count() == session.total_instances():
            incorrect_count = instance_answers.filter(correct=False).count()
            if incorrect_count > 0:
                correct = False
                points = 0
            else:
                correct = True
                points = self.default_points

            evaluation_object = Evaluation(correct=correct, points=points)
            evaluation_object.save()
            answer_object.evaluation = evaluation_object
            answer_object.save()


# ^
# |
# CONTENT TYPES
# EXERCISE SUBMODELS
# |
# V


class Hint(models.Model):
    """
    A hint that is linked to an exercise and shown to the user under
    configurable conditions.
    """

    exercise = models.ForeignKey(ContentPage, on_delete=models.CASCADE)
    hint = models.TextField(verbose_name="hint text")
    tries_to_unlock = models.IntegerField(
        default=0,
        verbose_name="number of tries to unlock this hint",
        help_text="Use 0 to show the hint immediately – before any answer attempts.",
    )

    class Meta:
        verbose_name = "configurable hint"


def default_fue_timeout():
    return datetime.timedelta(seconds=5)



class ExerciseOneToOneManager(models.Manager):

    def get_by_natural_key(self, exercise_slug):
        return self.get(exercise__slug=exercise_slug)


class FileExerciseSettings(models.Model):
    """
    A separate extra settings model for file upload exercises. Introduced to prevent
    contentpage model from expanding unnecessarily.
    """

    ANSWER_MODE_CHOICES = (
        ("FILE", "Upload as file"),
        ("TEXT", "From textbox"),
    )

    objects = ExerciseOneToOneManager()

    exercise = models.OneToOneField(
        FileUploadExercise,
        verbose_name="for file exercise",
        db_index=True,
        on_delete=models.CASCADE,
    )
    allowed_filenames = ArrayField(
        base_field=models.CharField(max_length=32, blank=True), default=list, blank=True
    )
    max_file_count = models.PositiveIntegerField(
        null=True,
        blank=True,
    )
    answer_mode = models.CharField(
        max_length=12,
        default="FILE",
        choices=ANSWER_MODE_CHOICES
    )
    answer_filename = models.CharField(
        max_length=32,
        null=True,
        blank=True,
        verbose_name=_("Filename to use for the answer"),
        help_text=_(
            "Required for tasks where answer mode is TEXT. "
            "For FILE, submitted file is renamed to this name "
            "unless multiple files are returned. For multiple "
            "files this does nothing."
        )
    )

    def natural_key(self):
        return (self.exercise.slug, )


class FileExerciseTestManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, name):
        return self.get(exercise__slug=exercise_slug, name=name)

class FileExerciseTest(models.Model, ExportImportMixin):
    class Meta:
        verbose_name = "file exercise test"

    objects = FileExerciseTestManager()

    exercise = models.ForeignKey(
        FileUploadExercise,
        verbose_name="for file exercise",
        db_index=True,
        on_delete=models.CASCADE,
    )
    name = models.CharField(verbose_name="Test name", max_length=200)

    # Note: only allow selection of files that have been linked to the exercise!
    required_files = models.ManyToManyField(
        "FileExerciseTestIncludeFile", verbose_name="files required by this test", blank=True
    )
    required_instance_files = models.ManyToManyField(
        "InstanceIncludeFile", verbose_name="instance files required by this test", blank=True
    )

    def natural_key(self):
        return (self.exercise.slug, self.name)

    def __str__(self):
        return self.name

    def export(self, instance, export_target):
        super().export(instance, export_target)
        for stage in self.fileexerciseteststage_set.get_queryset():
            stage.export(instance, export_target)


class FileExerciseTestStageManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, test_name, ordinal):
        return self.get(
            test__exercise__slug=exercise_slug,
            test__name=test_name,
            ordinal_number=ordinal
        )

class FileExerciseTestStage(models.Model, ExportImportMixin):
    """A stage – a named sequence of commands to run in a file exercise test."""

    class Meta:
        # Deferred constraints: https://code.djangoproject.com/ticket/20581
        unique_together = ("test", "ordinal_number")
        ordering = ["ordinal_number"]

    objects = FileExerciseTestStageManager()

    test = models.ForeignKey(FileExerciseTest, on_delete=models.CASCADE)
    depends_on = models.ForeignKey(
        "FileExerciseTestStage", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=64, default="stage")  # Translate
    ordinal_number = models.PositiveSmallIntegerField()

    def natural_key(self):
        return (self.test.exercise.slug, self.test.name, str(self.ordinal_number))

    def __str__(self):
        return f"{self.test.name}: {self.ordinal_number:02} - {self.name}"

    def export(self, instance, export_target):
        super().export(instance, export_target)
        for command in self.fileexercisetestcommand_set.get_queryset():
            command.export(instance, export_target)


class FileExerciseTestCommandManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, test_name, stage_ordinal, ordinal):
        return self.get(
            stage__test__exercise__slug=exercise_slug,
            stage__test__name=test_name,
            stage__ordinal_number=stage_ordinal,
            ordinal_number=ordinal
        )



class FileExerciseTestCommand(models.Model, ExportImportMixin):
    """A command that shall be executed on the test machine."""

    class Meta:
        verbose_name = "command to run for the test"
        verbose_name_plural = "commands to run for the test"
        # Deferred constraints: https://code.djangoproject.com/ticket/20581
        unique_together = ("stage", "ordinal_number")
        ordering = ["ordinal_number"]

    POSIX_SIGNALS_CHOICES = (
        ("None", "Don't send any signals"),
        ("SIGINT", "Interrupt signal (same as Ctrl-C)"),
        ("SIGTERM", "Terminate signal"),
    )

    objects = FileExerciseTestCommandManager()

    stage = models.ForeignKey(FileExerciseTestStage, on_delete=models.CASCADE)
    command_line = models.CharField(max_length=255)  # Translate
    significant_stdout = models.BooleanField(
        verbose_name="Compare the generated stdout to reference",
        default=False,
        help_text="Determines whether the"
        " standard output generated by "
        "this command is compared to the "
        "one generated by running this "
        "command with the reference files.",
    )
    significant_stderr = models.BooleanField(
        verbose_name="Compare the generated stderr to reference",
        default=False,
        help_text=(
            "Determines whether the standard errors generated by this command are compared"
            " to those generated by running this command with the reference files."
        ),
    )
    json_output = models.BooleanField(
        verbose_name="Test results as JSON",
        default=False,
        help_text="The checker provides test results as JSON",
    )
    timeout = models.DurationField(
        default=default_fue_timeout,
        help_text="How long is the command allowed to run before termination?",
    )
    signal = models.CharField(
        max_length=8,
        default="None",
        choices=POSIX_SIGNALS_CHOICES,
        help_text="Which POSIX signal shall be fired at the program?",
    )
    input_text = models.TextField(
        verbose_name="Input fed to the command through STDIN",
        blank=True,  # Translate
        help_text="What input shall be entered to the program's stdin upon execution?",
    )
    return_value = models.IntegerField(verbose_name="Expected return value", blank=True, null=True)
    ordinal_number = models.PositiveSmallIntegerField()  # TODO: Enforce min=1

    def natural_key(self):
        return list(self.stage.natural_key()) + [str(self.ordinal_number)]

    def __str__(self):
        return f"{self.ordinal_number:02}: {self.command_line}"

    def export(self, instance, export_target):
        super().export(instance, export_target)
        name = "_".join(self.natural_key())
        export_json(
            serialize_many_python(
                FileExerciseTestExpectedOutput.objects.filter(command=self, output_type="STDOUT")
            ),
            f"{name}_exp_stdout",
            export_target,
        )
        export_json(
            serialize_many_python(
                FileExerciseTestExpectedOutput.objects.filter(command=self, output_type="STDERR")
            ),
            f"{name}_exp_stderr",
            export_target,
        )


class FileExerciseTestExpectedOutput(models.Model):
    """What kind of output is expected from the program?"""

    OUTPUT_TYPE_CHOICES = (
        ("STDOUT", "Standard output (stdout)"),
        ("STDERR", "Standard error (stderr)"),
    )

    command = models.ForeignKey(FileExerciseTestCommand, on_delete=models.CASCADE)
    correct = models.BooleanField(default=False)
    regexp = models.BooleanField(default=False)
    expected_answer = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    output_type = models.CharField(max_length=7, default="STDOUT", choices=OUTPUT_TYPE_CHOICES)


class FileExerciseTestExpectedStdout(FileExerciseTestExpectedOutput):
    class Meta:
        verbose_name = "expected output"
        proxy = True

    def save(self, *args, **kwargs):
        self.output_type = "STDOUT"
        super().save(*args, **kwargs)


class FileExerciseTestExpectedStderr(FileExerciseTestExpectedOutput):
    class Meta:
        verbose_name = "expected error"
        proxy = True

    def save(self, *args, **kwargs):
        self.output_type = "STDERR"
        super().save(*args, **kwargs)


# ^
# |
# EXERCISE SUBMODELS
# INSTANCE FILES
# |
# V


class InstanceFileExerciseLinkManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, file_slug):
        return self.get(exercise__slug=exercise_slug, include_file__slug=file_slug)

class InstanceIncludeFileToExerciseLink(models.Model, ExportImportMixin):
    """
    Context model for shared course files for file exercises.
    """

    objects = InstanceFileExerciseLinkManager()

    include_file = models.ForeignKey("InstanceIncludeFile", on_delete=models.CASCADE)
    exercise = models.ForeignKey("ContentPage", on_delete=models.CASCADE)

    # The settings are determined per exercise basis
    file_settings = models.ForeignKey("IncludeFileSettings", on_delete=models.CASCADE)

    def natural_key(self):
        return (self.exercise.slug, self.include_file.slug)

    def export(self, instance, export_target):
        document = serialize_single_python(self)
        name = "_".join(self.natural_key()) + "_link"
        export_json(document, name, export_target)
        export_json(
            serialize_single_python(self.file_settings),
            f"{name}_settings",
            export_target,
        )


class InstanceFileLinkManager(models.Manager):

    def get_by_natural_key(self, instance_slug, file_name):
        return self.get(instance__slug=instance_slug, include_file__default_name=file_name)


class InstanceIncludeFileToInstanceLink(models.Model, ExportImportMixin):
    class Meta:
        unique_together = ("instance", "include_file")

    objects = InstanceFileLinkManager()

    revision = models.PositiveIntegerField(blank=True, null=True)
    instance = models.ForeignKey("CourseInstance", on_delete=models.CASCADE)
    include_file = models.ForeignKey("InstanceIncludeFile", on_delete=models.CASCADE)

    def natural_key(self):
        return [self.instance.slug, self.include_file.default_name]

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "include_file", freeze_to)

    def set_instance(self, instance):
        self.instance = instance






class InstanceIncludeFile(models.Model):
    """
    A file that's linked to a course and can be included in any exercise
    that needs it. (File upload, code input, code replace, ...)
    """

    objects = SlugManager()

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercises = models.ManyToManyField(
        ContentPage,
        blank=True,
        through="InstanceIncludeFileToExerciseLink",
        through_fields=("include_file", "exercise"),
    )
    default_name = models.CharField(verbose_name="Default name", max_length=255)  # Translate
    slug = models.SlugField(
        max_length=255, db_index=True, unique=True, blank=False, allow_unicode=True
    )
    description = models.TextField(blank=True, null=True)  # Translate
    fileinfo = models.FileField(
        max_length=255, upload_to=get_instancefile_path, storage=upload_storage
    )  # Translate

    def natural_key(self):
        return [self.slug]

    def save(self, *args, **kwargs):
        new = False
        if self.pk is None:
            new = True
        self.slug = get_prefixed_slug(self, self.course, "default_name")
        super().save(*args, **kwargs)
        if new:
            self.create_instance_links()

    def get_file_contents(self):
        file_contents = None
        with open(self.fileinfo.path, "rb") as f:
            file_contents = f.read()
        return file_contents

    def create_instance_links(self):
        active_instances = CourseInstance.objects.filter(course=self.course, frozen=False)
        for instance in active_instances:
            link = InstanceIncludeFileToInstanceLink(
                revision=None, instance=instance, include_file=self
            )
            link.save()

    def export(self, instance, export_target):
        document = serialize_single_python(self)
        name = self.slug
        export_json(document, name, export_target)
        export_files(self, export_target, "backend", translate=True)

# ^
# |
# INSTANCE FILES
# EXERCISE FILES
# |
# V


class IncludeFileManager(models.Manager):

    def get_by_natural_key(self, export_id):
        return self.get(export_id=export_id)

class FileExerciseTestIncludeFile(models.Model):
    """
    A file which an admin can include in an exercise's file pool for use in
    tests. For example, a reference program, expected output file or input file
    for the program.
    """

    class Meta:
        verbose_name = "included file"

    objects = IncludeFileManager()
    exercise = models.ForeignKey(FileUploadExercise, on_delete=models.CASCADE)
    export_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    file_settings = models.ForeignKey("IncludeFileSettings", on_delete=models.CASCADE)
    default_name = models.CharField(verbose_name="Default name", max_length=255)  # Translate
    description = models.TextField(blank=True, null=True)  # Translate
    fileinfo = models.FileField(
        max_length=255, upload_to=get_testfile_path, storage=upload_storage
    )  # Translate


    def natural_key(self):
        return [self.export_id]

    def __str__(self):
        return f"{self.file_settings.purpose} - {self.default_name}"

    def get_filename(self):
        return os.path.basename(self.fileinfo.name)

    def get_file_contents(self):
        file_contents = None
        with open(self.fileinfo.path, "rb") as f:
            file_contents = f.read()
        return file_contents

    def export(self, instance, export_target):
        document = serialize_single_python(self)
        name = f"{self.default_name}_{self.export_id}"
        export_json(
            document,
            name,
            export_target,
        )
        export_json(
            serialize_single_python(self.file_settings),
            f"{name}_settings",
            export_target,
        )
        export_files(self, export_target, "backend", translate=True)



# Export ID needed to be added for this to be importable with
# natural keys
class FileSettingsManager(models.Manager):

    def get_by_natural_key(self, export_id):
        return self.get(
            export_id=export_id
        )


class IncludeFileSettings(models.Model):
    FILE_OWNERSHIP_CHOICES = (
        ("OWNED", "Owned by the tested program"),
        ("NOT_OWNED", "Not owned by the tested program"),
    )
    FILE_PURPOSE_CHOICES = (
        ("Files written into the test directory for reading", (("INPUT", "Input file"),)),
        ("Files the program is expected to generate", (("OUTPUT", "Expected output file"),)),
        (
            "Executable files",
            (
                ("LIBRARY", "Library file"),
                ("REFERENCE", "Reference implementation"),
                ("INPUTGEN", "Input generator"),
                ("WRAPPER", "Wrapper for uploaded code"),
                ("TEST", "Unit test"),
            ),
        ),
    )

    objects = FileSettingsManager()

    # Default order: reference, inputgen, wrapper, test
    name = models.CharField(verbose_name="File name during test", max_length=255)  # Translate
    export_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    purpose = models.CharField(
        verbose_name="Used as", max_length=10, default="REFERENCE", choices=FILE_PURPOSE_CHOICES
    )
    chown_settings = models.CharField(
        verbose_name="File user ownership",
        max_length=10,
        default="OWNED",
        choices=FILE_OWNERSHIP_CHOICES,
    )
    chgrp_settings = models.CharField(
        verbose_name="File group ownership",
        max_length=10,
        default="OWNED",
        choices=FILE_OWNERSHIP_CHOICES,
    )
    chmod_settings = models.CharField(
        verbose_name="File access mode", max_length=10, default="rw-rw-r--"
    )

    def natural_key(self):
        return [self.export_id]


# ^
# |
# EXERCISE FILES
# ANSWER MODELS
# |
# V


class AnswerModelManager(models.Manager):

    def get_by_natural_key(self, exercise_slug, ordinal):
        return self.get(exercise__slug=exercise_slug, ordinal=ordinal)


class TextfieldExerciseAnswer(models.Model):
    objects = AnswerModelManager()

    exercise = models.ForeignKey(TextfieldExercise, on_delete=models.CASCADE)
    correct = models.BooleanField(default=False)
    regexp = models.BooleanField(default=True)
    answer = models.TextField()  # Translate
    hint = models.TextField(blank=True)  # Translate
    comment = models.TextField(
        verbose_name="Extra comment given upon entering a matching answer", blank=True
    )  # Translate
    ordinal = models.PositiveIntegerField()

    def __str__(self):
        if len(self.answer) > 76:
            return self.answer[0:76] + " ..."
        return self.answer

    def natural_key(self):
        return [self.exercise.slug, self.ordinal]

    def save(self, *args, **kwargs):
        self.answer = self.answer.replace("\r", "")
        if self.ordinal is None:
            previous = TextfieldExerciseAnswer.objects.filter(
                exercise=self.exercise,
            ).order_by("-ordinal").first()
            if previous and previous.ordinal is not None:
                self.ordinal = previous.ordinal + 1
            else:
                self.ordinal = 1
        super().save(*args, **kwargs)


class MultipleChoiceExerciseAnswer(models.Model):
    objects = AnswerModelManager()

    exercise = models.ForeignKey(MultipleChoiceExercise, null=True, on_delete=models.SET_NULL)
    correct = models.BooleanField(default=False)
    ordinal = models.PositiveIntegerField()
    answer = models.TextField()  # Translate
    hint = models.TextField(blank=True)  # Translate
    comment = models.TextField(
        verbose_name="Extra comment given upon selection of this answer", blank=True
    )  # Translate

    def __str__(self):
        return self.answer

    def natural_key(self):
        return [self.exercise.slug, self.ordinal]


class CheckboxExerciseAnswer(models.Model):
    objects = AnswerModelManager()

    exercise = models.ForeignKey(CheckboxExercise, null=True, on_delete=models.SET_NULL)
    correct = models.BooleanField(default=False)
    ordinal = models.PositiveIntegerField()
    answer = models.TextField()  # Translate
    hint = models.TextField(blank=True)  # Translate
    comment = models.TextField(
        verbose_name="Extra comment given upon selection of this answer", blank=True
    )  # Translate

    def __str__(self):
        return self.answer

    def natural_key(self):
        return [self.exercise.slug, self.ordinal]

# ^
# |
# ANSWER MODELS
# TEMPLATE EXERCISE MODELS
# |
# V


class RepeatedTemplateExerciseTemplate(models.Model):
    exercise = models.ForeignKey(RepeatedTemplateExercise, on_delete=models.CASCADE)
    title = models.CharField(max_length=64)  # Translate
    content_string = models.TextField()  # Translate


class RepeatedTemplateExerciseBackendFile(models.Model):
    exercise = models.ForeignKey(RepeatedTemplateExercise, on_delete=models.CASCADE)
    filename = models.CharField(max_length=255, blank=True)
    fileinfo = models.FileField(max_length=255, upload_to=get_testfile_path, storage=upload_storage)

    def get_filename(self):
        return os.path.basename(self.fileinfo.name)

    def save(self, *args, **kwargs):
        if not self.filename:
            self.filename = os.path.basename(self.fileinfo.name)
        super().save(*args, **kwargs)

    def get_file_contents(self):
        file_contents = None
        with open(self.fileinfo.path, "rb") as f:
            file_contents = f.read()
        return file_contents


class RepeatedTemplateExerciseBackendCommand(models.Model):
    exercise = models.OneToOneField(RepeatedTemplateExercise, on_delete=models.CASCADE)
    command = models.TextField()  # Translate


class RepeatedTemplateExerciseSession(models.Model):
    exercise = models.ForeignKey(RepeatedTemplateExercise, on_delete=models.CASCADE)
    user = models.ForeignKey(User, blank=True, null=True, on_delete=models.SET_NULL)
    revision = models.PositiveIntegerField()
    language_code = models.CharField(max_length=7)
    generated_json = JSONField()

    def __str__(self):
        if self.user is not None:
            user = self.user.username
        else:
            user = "<no-one>"
        return (
            "<RepeatedTemplateExerciseSession: "
            f"id {self.id} for exercise id {self.exercise.id}, user {user}>"
        )

    def total_instances(self) -> int:
        total = RepeatedTemplateExerciseSessionInstance.objects.filter(session=self).aggregate(
            Max("ordinal_number")
        )
        return total["ordinal_number__max"] + 1


class RepeatedTemplateExerciseSessionInstance(models.Model):
    exercise = models.ForeignKey(RepeatedTemplateExercise, on_delete=models.CASCADE)
    session = models.ForeignKey(RepeatedTemplateExerciseSession, on_delete=models.CASCADE)
    template = models.ForeignKey(RepeatedTemplateExerciseTemplate, on_delete=models.CASCADE)
    ordinal_number = models.PositiveSmallIntegerField()
    variables = ArrayField(
        base_field=models.TextField(),
        default=list,
    )
    values = ArrayField(
        base_field=models.TextField(),
        default=list,
    )

    class Meta:
        ordering = ("ordinal_number",)
        unique_together = (
            "session",
            "ordinal_number",
        )

    def __str__(self):
        return (
            "<RepeatedTemplateExerciseSessionInstance: "
            f"no. {self.ordinal_number} of session {self.session.id}>"
        )


class RepeatedTemplateExerciseSessionInstanceAnswer(models.Model):
    session_instance = models.ForeignKey(
        RepeatedTemplateExerciseSessionInstance, null=True, on_delete=models.SET_NULL
    )
    correct = models.BooleanField()
    regexp = models.BooleanField()
    answer = models.TextField()
    hint = models.TextField(blank=True)
    comment = models.TextField(blank=True)

    def __str__(self):
        if len(self.answer) > 76:
            return self.answer[0:76] + " ..."
        return self.answer

    def save(self, *args, **kwargs):
        self.answer = self.answer.replace("\r", "")
        super().save(*args, **kwargs)


# ^
# |
# TEMPLATE EXERCISE MODELS
# USER ANSWER MODELS
# |
# V


class Evaluation(models.Model):
    """Evaluation of a student's answer to an exercise."""

    correct = models.BooleanField(default=False)
    suspect = models.BooleanField(default=False)
    points = models.DecimalField(default=0, max_digits=5, decimal_places=2)

    # max_points is separate from the task's default_points to allow
    # for flexibility in changing the point values of tasks.
    max_points = models.IntegerField(default=1)

    # Note: Evaluation should not be translated. The teacher should know which
    # language the student used and give an evaluation using that language.

    evaluation_date = models.DateTimeField(
        verbose_name="When was the answer evaluated", auto_now_add=True
    )
    evaluator = models.ForeignKey(
        User,
        verbose_name="Who evaluated the answer",
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
    )
    feedback = models.TextField(verbose_name="Feedback given by a teacher", blank=True)
    test_results = models.TextField(
        verbose_name="Test results in JSON", blank=True
    )  # TODO: JSONField
    comment = models.TextField(
        verbose_name="Comment about the evaluation for course staff only", blank=True
    )


class UserAnswer(models.Model):
    """
    Parent class for what users have given as their answers to different exercises.

    SET_NULL should be used as the on_delete behaviour for foreignkeys pointing to the
    exercises. The answers will then be kept even when the exercise is deleted.
    """

    html_extra_class = ""

    instance = models.ForeignKey(CourseInstance, null=True, on_delete=models.SET_NULL)
    evaluation = models.ForeignKey(Evaluation, null=True, blank=True, on_delete=models.SET_NULL)
    revision = models.PositiveIntegerField()  # The revision info is always required!
    language_code = models.CharField(max_length=7)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    answer_date = models.DateTimeField(
        verbose_name="Date and time of when the user answered this exercise", auto_now_add=True
    )
    answerer_ip = models.GenericIPAddressField()
    task_id = models.CharField(max_length=36, null=True, blank=True)

    collaborators = models.TextField(
        verbose_name="Which users was this exercise answered with", blank=True, null=True
    )
    checked = models.BooleanField(verbose_name="This answer has been checked", default=False)
    draft = models.BooleanField(verbose_name="This answer is a draft", default=False)

    # NOTE: This should be obsolete and replaced by content page's get_user_answers
    @staticmethod
    def get_task_answers(task, instance=None, user=None, revision=None):
        if task.content_type == "CHECKBOX_EXERCISE":
            answers = UserAnswer.objects.filter(usercheckboxexerciseanswer__exercise=task)
        elif task.content_type == "MULTIPLE_CHOICE_EXERCISE":
            answers = UserAnswer.objects.filter(usermultiplechoiceexerciseanswer__exercise=task)
        elif task.content_type == "TEXTFIELD_EXERCISE":
            answers = UserAnswer.objects.filter(usertextfieldexerciseanswer__exercise=task)
        elif task.content_type == "FILE_UPLOAD_EXERCISE":
            answers = UserAnswer.objects.filter(userfileuploadexerciseanswer__exercise=task)
        elif task.content_type == "REPEATED_TEMPLATE_EXERCISE":
            answers = UserAnswer.objects.filter(userrepeatedtemplateexerciseanswer__exercise=task)
        else:
            raise ValueError(f"Task {task} does not have a valid exercise type")

        if instance:
            answers = answers.filter(instance=instance)

        if user:
            answers = answers.filter(user=user)

        if revision:
            answers = answers.filter(revision=revision)

        return answers.order_by("answer_date")

    def get_html_repr(self, context):
        """
        A method that needs to be implemented by child classes to display answers in various
        answer tables (e.g. user answers and answer summary). Returns an HTML string. Receives
        the rendering context that is used for rendering the template itself. Refer to the
        embed_frame tag documentation in course_tags for more details about this context.
        """

        return ""


class FileUploadExerciseReturnFile(models.Model):
    """A file that a user returns for checking."""

    answer = models.ForeignKey("UserFileUploadExerciseAnswer", on_delete=models.CASCADE)
    fileinfo = models.FileField(
        max_length=255, upload_to=get_answerfile_path, storage=upload_storage
    )

    def filename(self):
        return os.path.basename(self.fileinfo.name)

    def get_type(self):
        try:
            mimetype = magic.from_file(self.fileinfo.path, mime=True)
        except UnicodeDecodeError as e:
            # ???
            # Assume binary
            binary = True
        else:
            text_part, type_part = mimetype.split("/")
            if text_part == "text":
                binary = False
            else:
                binary = True

        return (mimetype, binary)

    def get_content(self):
        if not self.get_type()[1]:
            path = self.fileinfo.path
            with open(path, "rb") as f:
                contents = f.read()
                try:
                    lexer = pygments.lexers.guess_lexer_for_filename(path, contents)
                except pygments.util.ClassNotFound:
                    return contents
                else:
                    return pygments.highlight(
                        contents, lexer, pygments.formatters.HtmlFormatter(nowrap=True)
                    )
        return ""


class UserFileUploadExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(
        FileUploadExercise, blank=True, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"Answer by {self.user.username}"

    def get_returned_files_raw(self):
        file_objects = FileUploadExerciseReturnFile.objects.filter(answer=self)
        returned_files = {}
        for returned_file in file_objects:
            path = returned_file.fileinfo.path
            with open(path, "rb") as f:
                contents = f.read()
                returned_files[returned_file.filename()] = contents
        return returned_files

    def get_returned_files(self):
        file_objects = FileUploadExerciseReturnFile.objects.filter(answer=self)
        returned_files = {}
        for returned_file in file_objects:
            path = returned_file.fileinfo.path
            with open(path, "rb") as f:
                contents = f.read()
                type_info = returned_file.get_type()
                if not type_info[1]:
                    try:
                        lexer = pygments.lexers.guess_lexer_for_filename(path, contents)
                    except pygments.util.ClassNotFound:
                        pass
                    else:
                        contents = pygments.highlight(
                            contents, lexer, pygments.formatters.HtmlFormatter(nowrap=True)
                        )
                returned_files[returned_file.filename()] = type_info + (contents,)
        return returned_files

    def get_returned_file_list(self):
        file_objects = FileUploadExerciseReturnFile.objects.filter(answer=self)
        returned_files = {}
        for returned_file in file_objects:
            type_info = returned_file.get_type()
            returned_files[returned_file.filename()] = type_info
        return returned_files

    def get_html_repr(self, context):
        returned_files = self.get_returned_file_list()
        repr_str = ""
        for fname, (type_info, contents) in returned_files.items():
            link_kw = {
                "user": context["student"],
                "course": context["course"],
                "instance": context["instance"],
                "answer": self,
                "filename": fname
            }
            dl_href = reverse("courses:download_answer_file", kwargs=link_kw)
            view_href = reverse("courses:show_answer_file", kwargs=link_kw)
            repr_str += f"<a class=\"file-url\" href=\"{dl_href}\" download></a>\n"
            if not contents:
                repr_str += (
                    f"<a class=\nfileview-link href=\"{view_href}\""
                    f"onclick=\"show_file(event, this)\">{fname}</a>\n"
                )
                repr_str += "<div class=\"popup\"><pre class=\"fileview\"></pre></div>"
            else:
                repr_str += fname
            repr_str += "<br />"
        return repr_str


class UserRepeatedTemplateInstanceAnswer(models.Model):
    answer = models.ForeignKey("UserRepeatedTemplateExerciseAnswer", on_delete=models.CASCADE)
    session_instance = models.ForeignKey(
        RepeatedTemplateExerciseSessionInstance, null=True, on_delete=models.SET_NULL
    )
    given_answer = models.TextField(blank=True)
    correct = models.BooleanField(default=False)

    def print_for_student(self):
        return f"{self.session_instance.ordinal_number + 1:02d}: {self.given_answer}"


class UserRepeatedTemplateExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(
        RepeatedTemplateExercise, blank=True, null=True, on_delete=models.SET_NULL
    )
    session = models.ForeignKey(
        RepeatedTemplateExerciseSession, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return f"Repeated template exercise answers by {self.user.username} to {self.exercise.name}"

    def get_instance_answers(self):
        return UserRepeatedTemplateInstanceAnswer.objects.filter(answer=self)


class UserTextfieldExerciseAnswer(UserAnswer):

    html_extra_class = "render-white-space monospace"

    exercise = models.ForeignKey(TextfieldExercise, null=True, on_delete=models.SET_NULL)
    given_answer = models.TextField()


    def __str__(self):
        return self.given_answer

    def get_html_repr(self, context):
        return self.given_answer


class UserMultipleChoiceExerciseAnswer(UserAnswer):

    html_extra_class = "render-white-space"

    exercise = models.ForeignKey(MultipleChoiceExercise, null=True, on_delete=models.SET_NULL)
    chosen_answer = models.ForeignKey(
        MultipleChoiceExerciseAnswer, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return str(self.chosen_answer)

    def is_correct(self):
        return self.chosen_answer.correct

    def get_html_repr(self, context):
        return self.chosen_answer



class UserCheckboxExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(CheckboxExercise, null=True, on_delete=models.SET_NULL)
    chosen_answers = models.ManyToManyField(CheckboxExerciseAnswer)

    def __str__(self):
        return ", ".join(str(a) for a in self.chosen_answers.all())

    def get_html_repr(self, context):
        repr_str = "<ul>\n"
        for chosen_answer in self.chosen_answers.all():
            repr_str += f"<li>{chosen_answer}</li>\n"
        repr_str += "</ul>\n"
        return repr_str




class UserTaskCompletion(models.Model):
    class Meta:
        unique_together = ("exercise", "instance", "user")

    exercise = models.ForeignKey(ContentPage, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    points = models.DecimalField(default=0, max_digits=8, decimal_places=5)
    state = models.CharField(
        max_length=16,
        choices=(
            ("unanswered", "The task has not been answered yet"),
            ("correct", "The task has been answered correctly"),
            ("incorrect", "The task has not been answered correctly"),
            ("credited", "The task has been credited by completing another task"),
            ("submitted", "An answer has been submitted, awaiting assessment"),
            ("ongoing", "The task has been started"),
        ),
    )


class InvalidExerciseAnswerException(Exception):
    """
    This exception is cast when an exercise answer cannot be processed.
    """


ContentPage.register_content_type("LECTURE", Lecture)
ContentPage.register_content_type(
    "MULTIPLE_CHOICE_EXERCISE", MultipleChoiceExercise, UserMultipleChoiceExerciseAnswer
)
ContentPage.register_content_type(
    "CHECKBOX_EXERCISE", CheckboxExercise, UserCheckboxExerciseAnswer
)
ContentPage.register_content_type(
    "TEXTFIELD_EXERCISE", TextfieldExercise, UserTextfieldExerciseAnswer
)
ContentPage.register_content_type(
    "FILE_UPLOAD_EXERCISE", FileUploadExercise, UserFileUploadExerciseAnswer
)

def get_import_list():
    return [
        Course,
        CourseInstance,
        Term,
        TermAlias,
        TermLink,
        TermTab,
        TermTag,
        CourseMedia,
        File,
        Image,
        VideoLink,
        InstanceIncludeFile,
        ContentPage,
        CheckboxExerciseAnswer,
        MultipleChoiceExerciseAnswer,
        TextfieldExerciseAnswer,
        FileExerciseSettings,
        IncludeFileSettings,
        FileExerciseTestIncludeFile,
        FileExerciseTest,
        FileExerciseTestStage,
        FileExerciseTestCommand,
        FileExerciseTestExpectedOutput,
        ContentGraph,
        EmbeddedLink,
        CourseMediaLink,
        InstanceIncludeFileToInstanceLink,
        InstanceIncludeFileToExerciseLink,
        TermToInstanceLink,
    ]


