"""Django database models for courses."""

import datetime
import itertools
import operator
import re
import os
from fnmatch import fnmatch
from html import escape

from django.conf import settings
from django.db import models
from django.db.models import Q, Max, JSONField
from django.contrib.auth.models import User, Group
from django.db.models.signals import post_save
from django.urls import reverse
from django.core.cache import cache
from django.template import loader
from django.utils import translation
from django.utils.translation import gettext as _
from django.utils.text import slugify
from django.contrib.postgres.fields import ArrayField
import django.conf

from reversion.models import Version

import pygments
import magic

import feedback.models
from utils.files import (
    get_answerfile_path,
    get_file_upload_path,
    get_image_upload_path,
    get_instancefile_path,
    get_testfile_path,
    upload_storage,
)
from utils.archive import get_archived_field, get_single_archived
from utils.management import freeze_context_link


class RollbackRevert(Exception):
    pass


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

    student_id = models.IntegerField(verbose_name="Student number", blank=True, null=True)
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


# ^
# |
# USER RELATED
# COURSE LEVEL
# |
# V


class Course(models.Model):
    """
    Describes the metadata for a course.
    """

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

    # TODO: Create an instance automatically, if none exists

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

    name = models.CharField(max_length=255, unique=True)  # Translate
    email = models.EmailField(blank=True)  # Translate
    slug = models.SlugField(max_length=255, allow_unicode=True, blank=False)
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
        default_lang = django.conf.settings.LANGUAGE_CODE
        return slugify(getattr(self, f"name_{default_lang}"), allow_unicode=True)

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
                instance.primary = False
                instance.save()

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

    def __str__(self):
        return self.name

    @property
    def get_identifying_str(self):
        return f"{self.course.name} / {self.name}"

    @property
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


class ContentGraph(models.Model):
    """A node in the course tree/graph. Links content into a course."""

    class Meta:
        unique_together = ("content", "instance")
        verbose_name = "content to course link"
        verbose_name_plural = "content to course links"

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

    def get_revision_str(self):
        if self.revision is None:
            return "newest"
        return f"rev. {self.revision}"

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "content", freeze_to)

    def __str__(self):
        return f"No. {self.ordinal_number} – {self.content.slug} ({self.get_revision_str()})"


# ^
# |
# COURSE LEVEL
# MEDIA
# |
# V


class CourseMedia(models.Model):
    """
    Top level model for embedded media.
    """

    name = models.CharField(
        verbose_name="Unique name identifier", max_length=200, unique=True
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for link in self.coursemedialink_set.get_queryset():
            if not link.instance.frozen:
                link.parent.regenerate_cache(link.instance)


class CourseMediaLink(models.Model):
    """
    Context model for embedded media.
    """

    media = models.ForeignKey(CourseMedia, on_delete=models.RESTRICT)
    parent = models.ForeignKey("ContentPage", on_delete=models.CASCADE, null=True)
    instance = models.ForeignKey(
        CourseInstance, verbose_name="Course instance", on_delete=models.CASCADE
    )
    revision = models.PositiveIntegerField(
        verbose_name="Revision to display", blank=True, null=True
    )

    class Meta:
        unique_together = ("instance", "media", "parent")

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "media", freeze_to)


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


class TermToInstanceLink(models.Model):
    term = models.ForeignKey("Term", on_delete=models.RESTRICT)
    instance = models.ForeignKey(
        CourseInstance, verbose_name="Course instance", on_delete=models.CASCADE
    )
    revision = models.PositiveIntegerField(
        verbose_name="Revision to display", blank=True, null=True
    )

    class Meta:
        unique_together = ("instance", "term")

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "term", freeze_to)


class Term(models.Model):
    course = models.ForeignKey(Course, verbose_name="Course", null=True, on_delete=models.SET_NULL)
    name = models.CharField(verbose_name="Term", max_length=200)  # Translate
    description = models.TextField()  # Translate

    tags = models.ManyToManyField("TermTag", blank=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for instance in CourseInstance.objects.filter(course=self.course, frozen=False):
            if not TermToInstanceLink.objects.filter(instance=instance, term=self):
                link = TermToInstanceLink(instance=instance, revision=None, term=self)
                link.save()

    class Meta:
        unique_together = (
            "course",
            "name",
        )


class TermAlias(models.Model):
    term = models.ForeignKey(Term, null=False, on_delete=models.CASCADE)
    name = models.CharField(verbose_name="Term", max_length=200)  # Translate


class TermTag(models.Model):
    name = models.CharField(verbose_name="Term", max_length=200)  # Translate

    def __str__(self):
        return self.name


class TermTab(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    title = models.CharField(verbose_name="Title of this tab", max_length=100)  # Translate
    description = models.TextField()  # Translate

    def __str__(self):
        return self.title


class TermLink(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    url = models.CharField(verbose_name="URL", max_length=300)  # Translate
    link_text = models.CharField(verbose_name="Link text", max_length=80)  # Translate


# ^
# |
# TERMS
# CALENDAR
# |
# V


class Calendar(models.Model):
    """A multi purpose calendar for course events markups, time reservations etc."""

    name = models.CharField(
        verbose_name="Name for reference in content", max_length=200, unique=True
    )
    allow_multiple = models.BooleanField(verbose_name="Allow multiple reservation", default=False)
    related_content = models.ForeignKey(
        "ContentPage", on_delete=models.SET_NULL, null=True, blank=True
    )

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


class EmbeddedLink(models.Model):
    parent = models.ForeignKey("ContentPage", related_name="emb_parent", on_delete=models.CASCADE)
    embedded_page = models.ForeignKey(
        "ContentPage", related_name="emb_embedded", on_delete=models.RESTRICT
    )
    revision = models.PositiveIntegerField(blank=True, null=True)
    ordinal_number = models.PositiveSmallIntegerField()
    instance = models.ForeignKey("CourseInstance", on_delete=models.CASCADE)

    class Meta:
        ordering = ["ordinal_number"]

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "embedded_page", freeze_to)


class ContentPage(models.Model):
    """
    A single content containing page of a course.
    The used content pages (Lecture and Exercise) and their
    child classes all inherit from this class.
    """

    class Meta:
        ordering = ("name",)

    CONTENT_TYPE_CHOICES = (
        ("LECTURE", "Lecture"),
        ("TEXTFIELD_EXERCISE", "Textfield exercise"),
        ("MULTIPLE_CHOICE_EXERCISE", "Multiple choice exercise"),
        ("CHECKBOX_EXERCISE", "Checkbox exercise"),
        ("FILE_UPLOAD_EXERCISE", "File upload exercise"),
#        ("CODE_INPUT_EXERCISE", "Code input exercise"),
#        ("CODE_REPLACE_EXERCISE", "Code replace exercise"),
        ("REPEATED_TEMPLATE_EXERCISE", "Repeated template exercise"),
        ("ROUTINE_EXERCISE", "Routine exercise"),
    )
    template = "courses/blank.html"

    name = models.CharField(max_length=255, help_text="The full name of this page")  # Translate
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

    # Exercise fields
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
    allowed_filenames = ArrayField(  # File upload exercise specific
        base_field=models.CharField(max_length=32, blank=True), default=list, blank=True
    )

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super().save(*args, **kwargs)

    def replace_lines(self, line_idx, new_lines, delete_count=1):
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
        HTML. If a rendered version already exists in the cache, use that
        instead.
        """
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

                #if isinstance(chunk, str):
                    #segment += chunk
                #if isinstance(chunk, markupparser.PageBreak):
                    #blocks.append(("plain", segment))
                    #segment = ""
                    #pages.append(blocks)
                    #blocks = []
                #else:
                    #blocks.append(("plain", segment))
                    #blocks.append(chunk)
                    #segment = ""

            #if segment:
                #blocks.append(("plain", segment))

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

        #for render in cached_content:
            #print(render)

        return cached_content

    def _get_rendered_content(self, context):
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
        from courses import blockparser

        question = blockparser.parseblock(escape(self.question, quote=False), context)
        return question

    def count_pages(self, instance):
        lang_code = translation.get_language()
        content_key = f"{self.slug}_contents_{instance.slug}_{lang_code}"
        keys = cache.keys(content_key + "*")
        return len(keys) - 1

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
        context = {"instance": instance, "course": instance.course, "content_page": self}
        if not active_only:
            try:
                revision = ContentGraph.objects.get(content=self, instance=instance).revision
            except ContentGraph.DoesNotExist:
                return
        else:
            revision = None

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
        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:courses_{adminized_type}_change", args=(self.id,))

    def get_url_name(self):
        default_lang = django.conf.settings.LANGUAGE_CODE
        return slugify(getattr(self, f"name_{default_lang}"), allow_unicode=True)

    def get_type_object(self):
        # this seems to lose the revision info?
        from routine_exercise.models import RoutineExercise

        type_models = {
            "LECTURE": Lecture,
            "TEXTFIELD_EXERCISE": TextfieldExercise,
            "MULTIPLE_CHOICE_EXERCISE": MultipleChoiceExercise,
            "CHECKBOX_EXERCISE": CheckboxExercise,
            "FILE_UPLOAD_EXERCISE": FileUploadExercise,
            "CODE_INPUT_EXERCISE": CodeInputExercise,
            "CODE_REPLACE_EXERCISE": CodeReplaceExercise,
            "REPEATED_TEMPLATE_EXERCISE": RepeatedTemplateExercise,
            "ROUTINE_EXERCISE": RoutineExercise,
        }
        return type_models[self.content_type].objects.get(id=self.id)

    def get_type_model(self):
        from routine_exercise.models import RoutineExercise

        type_models = {
            "LECTURE": Lecture,
            "TEXTFIELD_EXERCISE": TextfieldExercise,
            "MULTIPLE_CHOICE_EXERCISE": MultipleChoiceExercise,
            "CHECKBOX_EXERCISE": CheckboxExercise,
            "FILE_UPLOAD_EXERCISE": FileUploadExercise,
            "CODE_INPUT_EXERCISE": CodeInputExercise,
            "CODE_REPLACE_EXERCISE": CodeReplaceExercise,
            "REPEATED_TEMPLATE_EXERCISE": RepeatedTemplateExercise,
            "ROUTINE_EXERCISE": RoutineExercise,
        }
        return type_models[self.content_type]

    def get_answer_model(self):
        from routine_exercise.models import RoutineExerciseAnswer

        answer_models = {
            "LECTURE": None,
            "TEXTFIELD_EXERCISE": UserTextfieldExerciseAnswer,
            "MULTIPLE_CHOICE_EXERCISE": UserMultipleChoiceExerciseAnswer,
            "CHECKBOX_EXERCISE": UserCheckboxExerciseAnswer,
            "FILE_UPLOAD_EXERCISE": UserFileUploadExerciseAnswer,
            "CODE_INPUT_EXERCISE": None,
            "CODE_REPLACE_EXERCISE": UserCodeReplaceExerciseAnswer,
            "REPEATED_TEMPLATE_EXERCISE": UserRepeatedTemplateExerciseAnswer,
            "ROUTINE_EXERCISE": RoutineExerciseAnswer,
        }
        return answer_models[self.content_type]

    def is_answerable(self):
        return self.content_type != "LECTURE"

    def save_evaluation(self, user, evaluation, answer_object):
        """
        Evaluation dictionary:
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

    def update_evaluation(self, user, evaluation, answer_object, complete=True):
        from utils.exercise import update_completion
        from utils.users import get_group_members

        instance = answer_object.instance
        answer_object.evaluation.correct = evaluation["evaluation"]
        answer_object.evaluation.points = evaluation["points"]
        answer_object.evaluation.max_points = evaluation.get("max", self.default_points)
        answer_object.evaluation.feedback = evaluation.get("feedback", "")
        answer_object.evaluation.evaluator = evaluation.get("evaluator", None)
        answer_object.evaluation.save()
        if complete:
            update_completion(self, instance, user, evaluation, answer_object.answer_date)
            if self.group_submission:
                for member in get_group_members(user, instance):
                    update_completion(self, instance, member, evaluation, answer_object.answer_date)

    def get_user_evaluation(self, user, instance, check_group=True):
        try:
            completion = UserTaskCompletion.objects.get(user=user, instance=instance, exercise=self)
            return completion.state, completion.points
        except UserTaskCompletion.DoesNotExist:
            return "unanswered", 0

    def re_evaluate(self, user, instance):
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

    def get_user_answers(self, user, instance, ignore_drafts=True):
        raise NotImplementedError("base type has no method 'get_user_answers'")

    def get_feedback_questions(self):
        return [q.get_type_object() for q in self.feedback_questions.all()]

    def __str__(self):
        return self.name

    # HACK: Experimental way of implementing a better get_type_object
    # TODO: get rid of this
    def __getattribute__(self, name):
        if name == "get_choices":
            type_model = self.get_type_model()
            func = type_model.get_choices
        elif name == "get_rendered_content":
            type_model = self.get_type_model()
            func = type_model.get_rendered_content
        elif name == "get_question":
            type_model = self.get_type_model()
            func = type_model.get_question
        elif name == "get_admin_change_url":
            type_model = self.get_type_model()
            # Can be called from a template (without parameter)
            func = lambda: type_model.get_admin_change_url(self)
        elif name == "save_answer":
            type_model = self.get_type_model()
            func = type_model.save_answer
        elif name == "check_answer":
            type_model = self.get_type_model()
            func = type_model.check_answer
        elif name == "get_user_answers":
            type_model = self.get_type_model()
            func = type_model.get_user_answers
        elif name == "template":
            type_model = self.get_type_model()
            func = type_model.template
        else:
            return super().__getattribute__(name)
        return func


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

        return {"evaluation": correct, "hints": hints, "comments": comments}

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserMultipleChoiceExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserMultipleChoiceExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers


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

        return {"evaluation": correct, "hints": hints, "comments": comments}

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserCheckboxExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserCheckboxExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers


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

        return {"evaluation": correct, "hints": hints, "comments": comments, "errors": errors}

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserTextfieldExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserTextfieldExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers


class FileUploadExercise(ContentPage):
    class Meta:
        verbose_name = "file upload exercise"
        proxy = True

    template = "courses/file-upload-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "FILE_UPLOAD_EXERCISE"
        super().save(*args, **kwargs)
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
                if self.allowed_filenames not in ([], [""]):
                    for fnpat in self.allowed_filenames:
                        if fnmatch(uploaded_file.name, fnpat):
                            break
                    else:
                        raise InvalidExerciseAnswerException(
                            _(
                                "Filename {} is not listed in accepted filenames. Allowed:\n{}"
                            ).format(uploaded_file.name, ", ".join(self.allowed_filenames))
                        )

                return_file = FileUploadExerciseReturnFile(
                    answer=answer_object, fileinfo=uploaded_file
                )
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


# Placeholder for a textfield exercise variant where the answer is run as code in the backend
class CodeInputExercise(ContentPage):
    class Meta:
        verbose_name = "code input exercise"
        proxy = True

    template = "courses/code-input-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "CODE_INPUT_EXERCISE"
        super().save(*args, **kwargs)

    def get_user_answers(self, user, instance, ignore_drafts=True):
        return UserAnswer.objects.none()

    def save_answer(self, user, ip, answer, files, instance, revision):
        pass

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        return {}


# Placeholder for a textfield exercise variant where the student is allowed to modify part of
# a given code while the rest is kept fixed.
class CodeReplaceExercise(ContentPage):
    class Meta:
        verbose_name = "code replace exercise"
        proxy = True

    template = "courses/code-replace-exercise.html"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "CODE_REPLACE_EXERCISE"
        super().save(*args, **kwargs)
        parents = ContentPage.objects.filter(embedded_pages=self).distinct()
        for instance in CourseInstance.objects.filter(
            Q(contentgraph__content=self) | Q(contentgraph__content__embedded_pages=self),
            frozen=False,
        ).distinct():
            self.update_embedded_links(instance)
            for parent in parents:
                parent.regenerate_cache(instance)

    def get_choices(self, revision=None):
        choices = (
            CodeReplaceExerciseAnswer.objects.filter(exercise=self)
            .values_list("replace_file", "replace_line", "id")
            .order_by("replace_file", "replace_line")
        )
        choices = itertools.groupby(choices, operator.itemgetter(0))
        # Django templates don't like groupby, so evaluate iterators:
        return [(a, list(b)) for a, b in choices]

    def get_rendered_content(self, context):
        return ContentPage._get_rendered_content(self, context)

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def save_answer(self, user, ip, answer, files, instance, revision):
        pass

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        return {}

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            answers = UserCodeReplaceExerciseAnswer.objects.filter(exercise=self, user=user)
        else:
            answers = UserCodeReplaceExerciseAnswer.objects.filter(
                exercise=self, instance=instance, user=user
            )
        return answers


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
                    errors.append(f"Contact staff, regexp error '{e}' from regexp: {answer.answer}")
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


class FileExerciseTest(models.Model):
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

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "file exercise test"


class FileExerciseTestStage(models.Model):
    """A stage – a named sequence of commands to run in a file exercise test."""

    class Meta:
        # Deferred constraints: https://code.djangoproject.com/ticket/20581
        unique_together = ("test", "ordinal_number")
        ordering = ["ordinal_number"]

    test = models.ForeignKey(FileExerciseTest, on_delete=models.CASCADE)
    depends_on = models.ForeignKey(
        "FileExerciseTestStage", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=64, default="stage")  # Translate
    ordinal_number = models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.test.name}: {self.ordinal_number:02} - {self.name}"


class FileExerciseTestCommand(models.Model):
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

    def __str__(self):
        return f"{self.ordinal_number:02}: {self.command_line}"


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


class InstanceIncludeFileToExerciseLink(models.Model):
    """
    Context model for shared course files for file exercises.
    """

    include_file = models.ForeignKey("InstanceIncludeFile", on_delete=models.CASCADE)
    exercise = models.ForeignKey("ContentPage", on_delete=models.CASCADE)

    # The settings are determined per exercise basis
    file_settings = models.OneToOneField("IncludeFileSettings", on_delete=models.CASCADE)


class InstanceIncludeFileToInstanceLink(models.Model):
    class Meta:
        unique_together = ("instance", "include_file")

    revision = models.PositiveIntegerField(blank=True, null=True)
    instance = models.ForeignKey("CourseInstance", on_delete=models.CASCADE)
    include_file = models.ForeignKey("InstanceIncludeFile", on_delete=models.CASCADE)

    def freeze(self, freeze_to=None):
        freeze_context_link(self, "include_file", freeze_to)


class InstanceIncludeFile(models.Model):
    """
    A file that's linked to a course and can be included in any exercise
    that needs it. (File upload, code input, code replace, ...)
    """

    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    exercises = models.ManyToManyField(
        ContentPage,
        blank=True,
        through="InstanceIncludeFileToExerciseLink",
        through_fields=("include_file", "exercise"),
    )
    default_name = models.CharField(verbose_name="Default name", max_length=255)  # Translate
    description = models.TextField(blank=True, null=True)  # Translate
    fileinfo = models.FileField(
        max_length=255, upload_to=get_instancefile_path, storage=upload_storage
    )  # Translate

    def save(self, *args, **kwargs):
        new = False
        if self.pk is None:
            new = True
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


# ^
# |
# INSTANCE FILES
# EXERCISE FILES
# |
# V


class FileExerciseTestIncludeFile(models.Model):
    """
    A file which an admin can include in an exercise's file pool for use in
    tests. For example, a reference program, expected output file or input file
    for the program.
    """

    class Meta:
        verbose_name = "included file"

    exercise = models.ForeignKey(FileUploadExercise, on_delete=models.CASCADE)
    file_settings = models.OneToOneField("IncludeFileSettings", on_delete=models.CASCADE)
    default_name = models.CharField(verbose_name="Default name", max_length=255)  # Translate
    description = models.TextField(blank=True, null=True)  # Translate
    fileinfo = models.FileField(
        max_length=255, upload_to=get_testfile_path, storage=upload_storage
    )  # Translate

    def __str__(self):
        return f"{self.file_settings.purpose} - {self.default_name}"

    def get_filename(self):
        return os.path.basename(self.fileinfo.name)

    def get_file_contents(self):
        file_contents = None
        with open(self.fileinfo.path, "rb") as f:
            file_contents = f.read()
        return file_contents


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
    # Default order: reference, inputgen, wrapper, test
    name = models.CharField(verbose_name="File name during test", max_length=255)  # Translate
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
        verbose_name="File access mode", max_length=10, default="rw-rw-rw-"
    )


# ^
# |
# INSTANCE FILES
# ANSWER MODELS
# |
# V


class TextfieldExerciseAnswer(models.Model):
    exercise = models.ForeignKey(TextfieldExercise, on_delete=models.CASCADE)
    correct = models.BooleanField(default=False)
    regexp = models.BooleanField(default=True)
    answer = models.TextField()  # Translate
    hint = models.TextField(blank=True)  # Translate
    comment = models.TextField(
        verbose_name="Extra comment given upon entering a matching answer", blank=True
    )  # Translate

    def __str__(self):
        if len(self.answer) > 76:
            return self.answer[0:76] + " ..."
        return self.answer

    def save(self, *args, **kwargs):
        self.answer = self.answer.replace("\r", "")
        super().save(*args, **kwargs)


class MultipleChoiceExerciseAnswer(models.Model):
    exercise = models.ForeignKey(MultipleChoiceExercise, null=True, on_delete=models.SET_NULL)
    correct = models.BooleanField(default=False)
    ordinal = models.PositiveIntegerField(null=True)
    answer = models.TextField()  # Translate
    hint = models.TextField(blank=True)  # Translate
    comment = models.TextField(
        verbose_name="Extra comment given upon selection of this answer", blank=True
    )  # Translate

    def __str__(self):
        return self.answer


class CheckboxExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CheckboxExercise, null=True, on_delete=models.SET_NULL)
    correct = models.BooleanField(default=False)
    ordinal = models.PositiveIntegerField(null=True)
    answer = models.TextField()  # Translate
    hint = models.TextField(blank=True)  # Translate
    comment = models.TextField(
        verbose_name="Extra comment given upon selection of this answer", blank=True
    )  # Translate

    def __str__(self):
        return self.answer


class CodeInputExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CodeInputExercise, on_delete=models.CASCADE)
    answer = models.TextField()  # Translate


class CodeReplaceExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CodeReplaceExercise, on_delete=models.CASCADE)
    answer = models.TextField()  # Translate
    # replace_file = models.ForeignKey()
    replace_file = models.TextField()  # DEBUG
    replace_line = models.PositiveIntegerField()


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


class UserAnswer(models.Model):
    """
    Parent class for what users have given as their answers to different exercises.

    SET_NULL should be used as the on_delete behaviour for foreignkeys pointing to the
    exercises. The answers will then be kept even when the exercise is deleted.
    """

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
    exercise = models.ForeignKey(TextfieldExercise, null=True, on_delete=models.SET_NULL)
    given_answer = models.TextField()

    def __str__(self):
        return self.given_answer


class UserMultipleChoiceExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(MultipleChoiceExercise, null=True, on_delete=models.SET_NULL)
    chosen_answer = models.ForeignKey(
        MultipleChoiceExerciseAnswer, null=True, on_delete=models.SET_NULL
    )

    def __str__(self):
        return str(self.chosen_answer)

    def is_correct(self):
        return self.chosen_answer.correct


class UserCheckboxExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(CheckboxExercise, null=True, on_delete=models.SET_NULL)
    chosen_answers = models.ManyToManyField(CheckboxExerciseAnswer)

    def __str__(self):
        return ", ".join(str(a) for a in self.chosen_answers.all())


class CodeReplaceExerciseReplacement(models.Model):
    answer = models.ForeignKey("UserCodeReplaceExerciseAnswer", on_delete=models.CASCADE)
    target = models.ForeignKey(CodeReplaceExerciseAnswer, null=True, on_delete=models.SET_NULL)
    replacement = models.TextField()


class UserCodeReplaceExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(CodeReplaceExercise, null=True, on_delete=models.SET_NULL)
    given_answer = models.TextField()

    def __str__(self):
        return self.given_answer


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
