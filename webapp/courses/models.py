"""Django database models for courses."""
# TODO: Refactor into multiple apps
# TODO: Serious effort to normalize the db!
# TODO: Profile the app and add relevant indexes!
# TODO: Add on_delete to ForeignKeys to comply with Django 2.0 requirements.

import datetime
import itertools
import operator
import re
import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse
from django.utils.text import slugify as slugify
from django.contrib.postgres.fields import ArrayField

from reversion import revisions as reversion

import pygments
import magic

import courses.tasks as rpc_tasks

from feedback.models import ContentFeedbackQuestion

import courses.markupparser as markupparser

# TODO: Extend the registration system to allow users to enter the profile data!
# TODO: Separate profiles for students and teachers
class UserProfile(models.Model):
    """User profile, which extends the Django's User model."""
    # For more information, see:
    # https://docs.djangoproject.com/en/dev/topics/auth/#storing-additional-information-about-users
    # http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
    user = models.OneToOneField(User)
    
    student_id = models.IntegerField(verbose_name='Student number', blank=True, null=True)
    study_program = models.CharField(verbose_name='Study program', max_length=80, blank=True, null=True)
    enrollment_year = models.PositiveSmallIntegerField(verbose_name='Year of enrollment', blank=True, null=True)

    def __str__(self):
        return "%s's profile" % self.user

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

# TODO: A user group system for allowing users to form groups
# - max users / group

# TODO: Abstract the exercise model to allow "an answering entity" to give the answer, be it a group or a student

@reversion.register()
class Course(models.Model):
    """
    Describes the metadata for a course.
    """
    name = models.CharField(max_length=255) # Translate
    code = models.CharField(verbose_name="Course code",
                            help_text="Course code, for e.g. universities",
                            max_length=64, blank=True, null=True)
    credits = models.DecimalField(verbose_name="Course credits",
                                  help_text="How many credits does the course "
                                  "yield on completion, for e.g. universities",
                                  max_digits=6, decimal_places=2,
                                  blank=True, null=True)
    description = models.TextField(blank=True, null=True) # Translate
    slug = models.SlugField(max_length=255, db_index=True, unique=True,
                            allow_unicode=True)
    prerequisites = models.ManyToManyField('Course',
                                           verbose_name="Prerequisite courses",
                                           blank=True)

    # TODO: Create an instance automatically, if none exists

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        # TODO: Ensure uniqueness! I.e. what happens when there's a clash
        # between two slugs (e.g. two courses named "programming course" and
        # "Programming_Course").
        return slugify(self.name, allow_unicode=True)

    def get_instances(self):
        return self.courseinstance_set.all().order_by('start_date')

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super(Course, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

class CourseEnrollment(models.Model):
    instance = models.ForeignKey('CourseInstance')
    student = models.ForeignKey(User)

    enrollment_date = models.DateTimeField(auto_now_add=True)
    application_note = models.TextField(blank=True) # The student can write an application
    ENROLLMENT_STATE_CHOICES = (
        ('WAITING', 'Waiting'),
        ('PROCESSING', 'Processing'),
        ('ACCEPTED', 'Accepted'),
        ('EXPELLED', 'Expelled'),
        ('DENIED', 'Denied'),
    )
    enrollment_state = models.CharField(max_length=11, default='WAITING',
                                        choices=ENROLLMENT_STATE_CHOICES)
    enrollment_note = models.TextField(blank=True) # The teacher can write a rationale

    def is_enrolled(self):
        return True if self.enrollment_state == 'ACCEPTED' else False

@reversion.register()
class CourseInstance(models.Model):
    """
    A running instance of a course. Contains details about the start and end
    dates of the course.
    """
    name = models.CharField(max_length=255) # Translate
    slug = models.SlugField(max_length=255, allow_unicode=True)
    course = models.ForeignKey('Course')
    
    start_date = models.DateTimeField(verbose_name='Date and time on which the course begins',blank=True,null=True)
    end_date = models.DateTimeField(verbose_name='Date and time on which the course ends',blank=True,null=True)
    active = models.BooleanField(verbose_name='Force this instance active',default=False)

    notes = models.TextField(verbose_name='Notes for this instance', blank=True) # Translate
    enrolled_users = models.ManyToManyField(User, blank=True,
                                            through='CourseEnrollment',
                                            through_fields=('instance', 'student'))
    manual_accept = models.BooleanField(verbose_name='Teachers accept enrollments manually',
                                        default=False)
    
    frontpage = models.ForeignKey('Lecture', blank=True, null=True) # TODO: Create one automatically!
    contents = models.ManyToManyField('ContentGraph', blank=True)   # TODO: Rethink the content graph system!

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        # TODO: Ensure uniqueness! I.e. what happens when there's a clash
        # between two slugs (e.g. two courses named "programming course" and
        # "Programming_Course").
        return slugify(self.name, allow_unicode=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super(CourseInstance, self).save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    #link the content graph nodes to this instead


class ContentGraph(models.Model):
    """A node in the course tree/graph. Links content into a course."""
    # TODO: Rethink the content graph system! Maybe directed graph is the best choice...
    # TODO: Take embedded content into account! (Maybe: automatically make content nodes from embedded content)
    # TODO: "Allow answering after deadline has passed" flag.
    parentnode = models.ForeignKey('self', null=True, blank=True)
    content = models.ForeignKey('ContentPage', null=True, blank=True)
    responsible = models.ManyToManyField(User, blank=True)
    compulsory = models.BooleanField(verbose_name='Must be answered correctly before proceeding to next exercise', default=False)
    deadline = models.DateTimeField(verbose_name='The due date for completing this exercise',blank=True,null=True)
    publish_date = models.DateTimeField(verbose_name='When does this exercise become available',blank=True,null=True)
    scored = models.BooleanField(verbose_name='Does this exercise affect scoring', default=True)
    require_correct_embedded = models.BooleanField(verbose_name='Embedded exercises must be answered correctly in order to mark this item as correct',default=True)
    ordinal_number = models.PositiveSmallIntegerField() # TODO: Enforce min=1
    visible = models.BooleanField(verbose_name='Is this content visible to students', default=True)
    revision = models.PositiveIntegerField(verbose_name='The spesific revision of the content', blank=True, null=True) # null = current

    def get_revision_str(self):
        return "rev. {}".format(self.revision) if self.revision is not None else "newest"
    
    def __str__(self):
        if not self.content:
            return "No linked content yet"
        return "{} ({})".format(self.content.slug, self.get_revision_str())

    class Meta:
        verbose_name = "content to course link"
        verbose_name_plural = "content to course links"

def get_file_upload_path(instance, filename):
    return os.path.join("files", "%s" % (filename))

class File(models.Model):
    """Metadata of an embedded or attached file that an admin has uploaded."""
    # TODO: Make the uploading user the default and don't allow it to change
    uploader = models.ForeignKey(User, null=True, blank=True) # Translate
    name = models.CharField(verbose_name='Name for reference in content',max_length=200,unique=True)
    date_uploaded = models.DateTimeField(verbose_name='date uploaded', auto_now_add=True)
    typeinfo = models.CharField(max_length=200)
    fileinfo = models.FileField(max_length=255, upload_to=get_file_upload_path) # Translate

    def __str__(self):
        return self.name

def get_image_upload_path(instance, filename):
    return os.path.join("images", "%s" % (filename))

class Image(models.Model):
    """Image"""
    # TODO: Make the uploading user the default and don't allow it to change
    uploader = models.ForeignKey(User, null=True, blank=True) # Translate
    name = models.CharField(verbose_name='Name for reference in content', max_length=200, unique=True)
    date_uploaded = models.DateTimeField(verbose_name='date uploaded', auto_now_add=True)
    description = models.CharField(max_length=500) # Translate
    fileinfo = models.ImageField(upload_to=get_image_upload_path) # Translate

    def __str__(self):
        return self.name

class VideoLink(models.Model):
    """Youtube link for embedded videos"""
    # TODO: Make the adding user the default and don't allow it to change
    added_by = models.ForeignKey(User, null=True, blank=True) # Translate
    name = models.CharField(verbose_name='Name for reference in content', max_length=200, unique=True)
    link = models.URLField() # Translate
    description = models.CharField(max_length=500) # Translate

    def __str__(self):
        return self.name

class Term(models.Model):
    instance = models.ForeignKey(CourseInstance, verbose_name="Course instance")
    name = models.CharField(verbose_name='Term', max_length=200) # Translate
    description = models.TextField() # Translate
    
    def __str__(self):
        return self.name

## Time reservation and event calendar system
class Calendar(models.Model):
    """A multi purpose calendar for course events markups, time reservations etc."""
    name = models.CharField(verbose_name='Name for reference in content', max_length=200, unique=True)

    def __str__(self):
        return self.name

class CalendarDate(models.Model):
    """A single date on a calendar."""
    calendar = models.ForeignKey(Calendar)
    event_name = models.CharField(verbose_name='Name of the event', max_length=200) # Translate
    event_description = models.CharField(verbose_name='Description', max_length=200, blank=True, null=True) # Translate
    start_time = models.DateTimeField(verbose_name='Starts at')
    end_time = models.DateTimeField(verbose_name='Ends at')
    reservable_slots = models.IntegerField(verbose_name='Amount of reservable slots')

    def __str__(self):
        return self.event_name

    def get_users(self):
        return self.calendarreservation_set.all().values(
            'user__username', 'user__first_name',
            'user__last_name', 'user__userprofile__student_id',
        )

class CalendarReservation(models.Model):
    """A single user-made reservation on a calendar date."""
    calendar_date = models.ForeignKey(CalendarDate)
    user = models.ForeignKey(User)

class EmbeddedLink(models.Model):
    parent = models.ForeignKey('ContentPage', related_name='emb_parent')
    embedded_page = models.ForeignKey('ContentPage', related_name='emb_embedded')
    revision = models.PositiveIntegerField()
    ordinal_number = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['ordinal_number']

## Content management
@reversion.register()
class ContentPage(models.Model):
    """
    A single content containing page of a course.
    The used content pages (Lecture and Exercise) and their
    child classes all inherit from this class.
    """
    name = models.CharField(max_length=255, help_text="The full name of this page") # Translate
    slug = models.SlugField(max_length=255, db_index=True, unique=True,
                            allow_unicode=True)
    content = models.TextField(verbose_name="Page content body", blank=True, null=True) # Translate
    default_points = models.IntegerField(default=1,
                                         help_text="The default points a user can gain by finishing this exercise correctly")
    access_count = models.PositiveIntegerField(editable=False,blank=True,null=True)
    tags = ArrayField( # consider: https://github.com/funkybob/django-array-tags
        base_field=models.CharField(max_length=32, blank=True), # TODO: Should tags be like slugs?
        default=list,
        blank=True
    )
    
    CONTENT_TYPE_CHOICES = (
        ('LECTURE', 'Lecture'),
        ('TEXTFIELD_EXERCISE', 'Textfield exercise'),
        ('MULTIPLE_CHOICE_EXERCISE', 'Multiple choice exercise'),
        ('CHECKBOX_EXERCISE', 'Checkbox exercise'),
        ('FILE_UPLOAD_EXERCISE', 'File upload exercise'),
        ('CODE_INPUT_EXERCISE', 'Code input exercise'),
        ('CODE_REPLACE_EXERCISE', 'Code replace exercise'),
    )
    content_type = models.CharField(max_length=28, default='LECTURE', choices=CONTENT_TYPE_CHOICES)
    embedded_pages = models.ManyToManyField('self', blank=True,
                                            through=EmbeddedLink, symmetrical=False,
                                            through_fields=('parent', 'embedded_page'))

    feedback_questions = models.ManyToManyField(ContentFeedbackQuestion, blank=True)

    # Exercise fields
    question = models.TextField(blank=True) # Translate
    manually_evaluated = models.BooleanField(verbose_name="This exercise is evaluated by hand", default=False)
    ask_collaborators = models.BooleanField(verbose_name="Ask the student to list collaborators", default=False)

    def rendered_markup(self, request=None, context=None, revision=None):
        """
        Uses the included MarkupParser library to render the page content into
        HTML. If a rendered version already exists in the cache, use that
        instead.
        """
        # TODO: Cache
        # TODO: Separate caching depending on the language!
        # TODO: Save the embedded pages as embedded content links
        # TODO: Take csrf protection into account; use cookies only
        #       - https://docs.djangoproject.com/en/1.7/ref/contrib/csrf/
        rendered = ""
        embedded_pages = []

        # Render the page
        markup_gen = markupparser.MarkupParser.parse(self.content, request, context, embedded_pages)
        for chunk in markup_gen:
            rendered += chunk

        # Update the embedded pages field if we are not rendering an old version.
        # Important! If we save the object with its old version info, it will
        # overwrite the current version!
        # TODO: Refactor this to save.
        if embedded_pages:
            embedded_page_objs = ContentPage.objects.filter(slug__in=list(zip(*embedded_pages))[0])
            self.embedded_pages.clear()
            for i, (embedded_page, rev_id) in enumerate(embedded_pages):
                if rev_id is None:
                    rev_id = 1 # TODO: Get the current revision
                page_obj = EmbeddedLink(
                    parent=self,
                    embedded_page=embedded_page_objs.get(slug=embedded_page),
                    revision=rev_id,
                    ordinal_number=i
                )
                page_obj.save()
                self.save()

        return rendered

    def get_human_readable_type(self):
        humanized_type = self.content_type.replace("_", " ").lower()
        return humanized_type

    def get_dashed_type(self):
        dashed_type = self.content_type.replace("_", "-").lower()
        return dashed_type

    def get_admin_change_url(self):
        adminized_type = self.content_type.replace("_", "").lower()
        return reverse("admin:courses_%s_change" % (adminized_type), args=(self.id,))

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        # TODO: Ensure uniqueness!
        return slugify(self.name, allow_unicode=True)

    def get_type_object(self):
        # this seems to lose the revision info?
        type_models = {
            "LECTURE" : Lecture,
            "TEXTFIELD_EXERCISE" : TextfieldExercise,
            "MULTIPLE_CHOICE_EXERCISE" : MultipleChoiceExercise,
            "CHECKBOX_EXERCISE" : CheckboxExercise,
            "FILE_UPLOAD_EXERCISE" : FileUploadExercise,
            "CODE_INPUT_EXERCISE" : CodeInputExercise,
            "CODE_REPLACE_EXERCISE" : CodeReplaceExercise,
        }
        return type_models[self.content_type].objects.get(id=self.id)

    def get_type_model(self):
        type_models = {
            "LECTURE" : Lecture,
            "TEXTFIELD_EXERCISE" : TextfieldExercise,
            "MULTIPLE_CHOICE_EXERCISE" : MultipleChoiceExercise,
            "CHECKBOX_EXERCISE" : CheckboxExercise,
            "FILE_UPLOAD_EXERCISE" : FileUploadExercise,
            "CODE_INPUT_EXERCISE" : CodeInputExercise,
            "CODE_REPLACE_EXERCISE" : CodeReplaceExercise,
        }
        return type_models[self.content_type]

    #def get_choices(self, revision=None):
        # Blank function for types that don't require this
        #pass

    def is_answerable(self):
        if self.content_type == "LECTURE":
            return False
        else:
            return True

    def save_evaluation(self, user, evaluation, answer_object):
        correct = evaluation["evaluation"]
        if correct == True:
            points = self.default_points
        else:
            points = 0
            
        evaluation_object = Evaluation(correct=correct, points=points)
        evaluation_object.save()
        answer_object.evaluation = evaluation_object
        answer_object.save()

    def get_user_evaluation(self, user):
        raise NotImplementedError("base type has no method 'get_user_evaluation'")

    def get_user_answers(self, user, ignore_drafts=True):
        raise NotImplementedError("base type has no method 'get_user_answers'")

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        # TODO: Run through content parser
        #       - Check for & report errors (all errors on same notice)
        #       - Put into Redis cache
        #       - Automatically link embedded pages (create/update an
        #         EmbeddedContentLink object)
        super(ContentPage, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

    # HACK: Experimental way of implementing a better get_type_object
    def __getattribute__(self, name):
        if name == "get_choices":
            type_model = self.get_type_model()
            func = type_model.get_choices
        elif name == "save_answer":
            type_model = self.get_type_model()
            func = type_model.save_answer
        elif name == "check_answer":
            type_model = self.get_type_model()
            func = type_model.check_answer
        elif name == "save_evaluation":
            type_model = self.get_type_model()
            func = type_model.save_evaluation
        elif name == "get_user_evaluation":
            type_model = self.get_type_model()
            func = type_model.get_user_evaluation
        elif name == "get_user_answers":
            type_model = self.get_type_model()
            func = type_model.get_user_answers
        else:
            return super(ContentPage, self).__getattribute__(name)
        return func
        

@reversion.register()
class Lecture(ContentPage):
    """A single page for a lecture."""

    def get_choices(self, revision=None):
        pass
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)
        
        self.content_type = "LECTURE"
        super(Lecture, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "lecture page"
        proxy = True

    def get_user_evaluation(self, user):
        pass

@reversion.register(follow=["multiplechoiceexerciseanswer_set"])
class MultipleChoiceExercise(ContentPage):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "MULTIPLE_CHOICE_EXERCISE"
        super(MultipleChoiceExercise, self).save(*args, **kwargs)

    def get_choices(self, revision=None):
        choices = MultipleChoiceExerciseAnswer.objects.filter(exercise=self.id).order_by('id')
        return choices

    def save_answer(self, user, ip, answer, files, instance, revision):
        keys = list(answer.keys())
        key = [k for k in keys if k.endswith("-radio")]
        if not key:
            raise InvalidAnswerException("No answer was picked!")
        answered = int(answer[key[0]])

        
        # FIX: DEBUG DEBUG DEBUG DEBUG
        if revision == "head": revision = 0
        # FIX: DEBUG DEBUG DEBUG DEBUG

        
        try:
            chosen_answer = MultipleChoiceExerciseAnswer.objects.get(id=answered)
        except MultipleChoiceExerciseAnswer.DoesNotExist as e:
            raise InvalidAnswerException("The received answer does not exist!")
        answer_object = UserMultipleChoiceExerciseAnswer(
            exercise_id=self.id, chosen_answer=chosen_answer, user=user,
            answerer_ip=ip, instance=instance, revision=revision,
        )
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        choices = self.get_choices(self)
        
        # quick hax:
        answered = int([v for k, v in answer.items() if k.endswith("-radio")][0])

        # Determine, if the given answer was correct and which hints to show
        correct = False
        hints = []
        comments = []
        for choice in choices:
            if answered == choice.id and choice.correct == True:
                correct = True
                if choice.comment:
                    comments.append(choice.comment)
            elif answered != choice.id and choice.correct == True:
                if choice.hint:
                    hints.append(choice.hint)
            elif answered == choice.id and choice.correct == False:
                if choice.hint:
                    hints.append(choice.hint)
                if choice.comment:
                    comments.append(choice.comment)
            
        return {"evaluation": correct, "hints": hints, "comments": comments}

    def get_user_evaluation(self, user):
        evaluations = Evaluation.objects.filter(useranswer__usermultiplechoiceexerciseanswer__exercise_id=self.id, useranswer__user=user)
        if not evaluations:
            return "unanswered"
        correct = evaluations.filter(correct=True).count() > 0
        return "correct" if correct else "incorrect"

    def get_user_answers(self, user, ignore_drafts=True):
        answers = UserMultipleChoiceExerciseAnswer.objects.filter(exercise=self, user=user)
        return answers

    class Meta:
        verbose_name = "multiple choice exercise"
        proxy = True

@reversion.register(follow=["checkboxexerciseanswer_set"])
class CheckboxExercise(ContentPage):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "CHECKBOX_EXERCISE"
        super(CheckboxExercise, self).save(*args, **kwargs)

    def get_choices(self, revision=None):
        if revision is None:
            choices = CheckboxExerciseAnswer.objects.filter(exercise=self.id).order_by('id')
        else:
            # We need an old version of _which_ answer choices pointed to this exercise
            old_version = reversion.get_for_object(self).get(revision=revision).object_version.object
            old_choices = old_version.get_type_object().checkboxexerciseanswer_set
            print(old_choices.all())
            choices = []
            for choice in old_choices.all():
                # ...and we need an old version of _each_ of those answer choices
                try:
                    old_choice = reversion.get_for_object(choice).get(revision=revision).object_version.object
                    choices.append(old_choice)
                except reversion.Version.DoesNotExist as e:
                    pass
        return choices

    def save_answer(self, user, ip, answer, files, instance, revision):
        chosen_answer_ids = [int(i) for i, _ in answer.items() if i.isdigit()]
        
        chosen_answers = CheckboxExerciseAnswer.objects.filter(id__in=chosen_answer_ids).\
                         values_list('id', flat=True)
        if set(chosen_answer_ids) != set(chosen_answers):
            raise InvalidAnswerException("One or more of the answers do not exist!")

        # FIX: DEBUG DEBUG DEBUG DEBUG
        if revision == "head": revision = 0
        # FIX: DEBUG DEBUG DEBUG DEBUG

        
        answer_object = UserCheckboxExerciseAnswer(
            exercise_id=self.id, user=user, answerer_ip=ip,
            instance=instance, revision=revision,
        )
        answer_object.save()
        answer_object.chosen_answers.add(*chosen_answers)
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        # Determine, if the given answer was correct and which hints to show


        # FIX: DEBUG DEBUG DEBUG DEBUG
        if revision == "head": revision = None
        # FIX: DEBUG DEBUG DEBUG DEBUG

        
        choices = self.get_choices(self, revision)
        
        # quick hax:
        answered = {choice.id: False for choice in choices}
        answered.update({int(i): True for i, _ in answer.items() if i.isdigit()})
        
        correct = True
        hints = []
        comments = []
        chosen = []
        for choice in choices:
            if answered[choice.id] == True and choice.correct == True and correct == True:
                correct = True
                chosen.append(choice)
                if choice.comment:
                    comments.append(choice.comment)
            elif answered[choice.id] == False and choice.correct == True:
                correct = False
                if choice.hint:
                    hints.append(choice.hint)
            elif answered[choice.id] == True and choice.correct == False:
                correct = False
                if choice.hint:
                    hints.append(choice.hint)
                if choice.comment:
                    comments.append(choice.comment)
                chosen.append(choice)

        return {"evaluation": correct, "hints": hints, "comments": comments}

    def get_user_evaluation(self, user):
        evaluations = Evaluation.objects.filter(useranswer__usercheckboxexerciseanswer__exercise=self, useranswer__user=user)
        if not evaluations:
            return "unanswered"
        correct = evaluations.filter(correct=True).count() > 0
        return "correct" if correct else "incorrect"

    def get_user_answers(self, user, ignore_drafts=True):
        answers = UserCheckboxExerciseAnswer.objects.filter(exercise=self, user=user)
        return answers

    class Meta:
        verbose_name = "checkbox exercise"
        proxy = True

@reversion.register(follow=["textfieldexerciseanswer_set"])
class TextfieldExercise(ContentPage):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "TEXTFIELD_EXERCISE"
        super(TextfieldExercise, self).save(*args, **kwargs)

    def get_choices(self, revision=None):
        choices = TextfieldExerciseAnswer.objects.filter(exercise=self.id)
        return choices

    def save_answer(self, user, ip, answer, files, instance, revision):
        if "answer" in answer.keys():
            given_answer = answer["answer"].replace("\r", "")
        else:
            raise InvalidAnswerException("Answer missing!")


        # FIX: DEBUG DEBUG DEBUG DEBUG
        if revision == "head": revision = 0
        # FIX: DEBUG DEBUG DEBUG DEBUG
        

        answer_object = UserTextfieldExerciseAnswer(
            exercise_id=self.id, given_answer=given_answer, user=user,
            answerer_ip=ip, instance=instance, revision=revision,
        )
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        answers = self.get_choices(self)

        # Determine, if the given answer was correct and which hints/comments to show
        correct = False
        hints = []
        comments = []
        errors = []
        
        if "answer" in answer.keys():
            given_answer = answer["answer"].replace("\r", "")
        else:
            return {"evaluation": False}

        def re_validate(db_ans, given_ans):
            m = re.match(db_ans, given_ans)
            return (m is not None, m)
        #re_validate = lambda db_ans, given_ans: re.match(db_ans, given_ans) is not None
        str_validate = lambda db_ans, given_ans: (db_ans == given_ans, None)

        for answer in answers:
            validate = re_validate if answer.regexp else str_validate

            try:
                match, m = validate(answer.answer, given_answer)
            except re.error as e:
                if user.is_staff:
                    errors.append("Contact staff, regexp error '{}' from regexp: {}".format(e, answer.answer))
                else:
                    errors.append("Contact staff! Regexp error '{}' in exercise '{}'.".format(e, content.name))
                correct = False
                continue

            sub = lambda text: text
            if m is not None and m.groupdict():
                groups = {re.escape("{{{k}}}".format(k=k)): v for k, v in m.groupdict().items() if v is not None}
                if groups:
                    pattern = re.compile("|".join((re.escape("{{{k}}}".format(k=k)) for k in m.groupdict().keys())))
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

        return {"evaluation": correct, "hints": hints, "comments": comments,
                "errors": errors}

    def get_user_evaluation(self, user):
        evaluations = Evaluation.objects.filter(useranswer__usertextfieldexerciseanswer__exercise=self, useranswer__user=user)
        if not evaluations:
            return "unanswered"
        correct = evaluations.filter(correct=True).count() > 0
        return "correct" if correct else "incorrect"

    def get_user_answers(self, user, ignore_drafts=True):
        answers = UserTextfieldExerciseAnswer.objects.filter(exercise=self, user=user)
        return answers

    class Meta:
        verbose_name = "text field exercise"
        proxy = True

@reversion.register()
class FileUploadExercise(ContentPage):
    # TODO: A field for restricting uploadable file names (e.g. by extension, like .py)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "FILE_UPLOAD_EXERCISE"
        super(FileUploadExercise, self).save(*args, **kwargs)

    def save_answer(self, user, ip, answer, files, instance, revision):
        answer_object = UserFileUploadExerciseAnswer(
            exercise=self, user=user, answerer_ip=ip
        )
        answer_object.save()
        
        if files:
            filelist = files.getlist('file')
            for uploaded_file in filelist:
                return_file = FileUploadExerciseReturnFile(
                    answer=answer_object, fileinfo=uploaded_file
                )
                return_file.save()
        else:
            raise InvalidAnswerException("No file was sent!")
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        result = rpc_tasks.run_tests.delay(user_id=user.id, exercise_id=self.id,
                                           answer_id=answer_object.id)
        return {"task_id": result.task_id}

    def get_user_evaluation(self, user):
        evaluations = Evaluation.objects.filter(useranswer__userfileuploadexerciseanswer__exercise=self, useranswer__user=user)
        if not evaluations:
            return "unanswered"
        correct = evaluations.filter(correct=True).count() > 0
        return "correct" if correct else "incorrect"

    def get_user_answers(self, user, ignore_drafts=True):
        answers = UserFileUploadExerciseAnswer.objects.filter(exercise=self, user=user)
        return answers

    class Meta:
        verbose_name = "file upload exercise"
        proxy = True

@reversion.register()
class CodeInputExercise(ContentPage):
    # TODO: A textfield exercise variant that's run like a file exercise (like in Viope)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "CODE_INPUT_EXERCISE"
        super(CodeInputExercise, self).save(*args, **kwargs)

    def save_answer(self, user, ip, answer, files, instance, revision):
        pass

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        return {}

    class Meta:
        verbose_name = "code input exercise"
        proxy = True

@reversion.register()
class CodeReplaceExercise(ContentPage):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "CODE_REPLACE_EXERCISE"
        super(CodeReplaceExercise, self).save(*args, **kwargs)

    def get_choices(self, revision=None):
        choices = CodeReplaceExerciseAnswer.objects.filter(exercise=self)\
                                           .values_list('replace_file', 'replace_line', 'id')\
                                           .order_by('replace_file', 'replace_line')
        choices = itertools.groupby(choices, operator.itemgetter(0))
        # Django templates don't like groupby, so evaluate iterators:
        return [(a, list(b)) for a, b in choices]

    def save_answer(self, user, ip, answer, files, instance, revision):
        pass

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        return {}

    def get_user_evaluation(self, user):
        evaluations = Evaluation.objects.filter(useranswer__usercodereplaceexerciseanswer__exercise=self, useranswer__user=user)
        if not evaluations:
            return "unanswered"
        correct = evaluations.filter(correct=True).count() > 0
        return "correct" if correct else "incorrect"
    
    def get_user_answers(self, user, ignore_drafts=True):
        answers = UserCodeReplaceExerciseAnswer.objects.filter(exercise=self, user=user)
        return answers

    class Meta:
        verbose_name = "code replace exercise"
        proxy = True

# TODO: Code exercise that is ranked
# 1. against others
#     * celery runs a tournament of uploaded algorithms
#     * the results are sorted by performance
#     * in content meta, display ranking as evaluation (gold, silver, bronze crowns for places 1-3)
# 2. by some known scale
#     * celery runs the uploaded algorithm against a reference
#     * the result is compared to some value (e.g. 94% recognition achieved)
#     * in content meta, display achieved performance as evaluation (e.g. 57%, 13857 iterations, 22 min)
# - participants can view all the results!
# Inspiration:
# - coding competitions (correctness + timing/cpu cycle restrictions)
# - artificial intelligence course (competing othello AI algorithms)
# - pattern recognition and neural networks course (performance of an pattern
#   recognition algorithm)
#class RankedCodeExercise(ContentPage):
    #def save(self, *args, **kwargs):
        #if not self.slug:
            #self.slug = self.get_url_name()
        #else:
            #self.slug = slugify(self.slug, allow_unicode=True)
#
        #self.content_type = "RANKED_CODE_EXERCISE"
        #super(RankedCodeExercise, self).save(*args, **kwargs)
#
    #class Meta:
        #proxy = True

# TODO: Group code exercise. All group members must return their own files!
# Inspiration:
# - computer networks I course

@reversion.register()
class Hint(models.Model):
    """
    A hint that is linked to an exercise and shown to the user under
    configurable conditions.
    """
    exercise = models.ForeignKey(ContentPage)
    hint = models.TextField(verbose_name="hint text")
    tries_to_unlock = models.IntegerField(default=0,
                                          verbose_name="number of tries to unlock this hint",
                                          help_text="Use 0 to show the hint immediately – before any answer attempts.")

    class Meta:
        verbose_name = "configurable hint"

## File exercise test related models
# TODO: whitelist for allowed file name extensions (e.g. only allow files that end ".py")
def default_timeout(): return datetime.time(0,0,5)

class FileExerciseTest(models.Model):
    exercise = models.ForeignKey(FileUploadExercise, verbose_name="for file exercise", db_index=True)
    name = models.CharField(verbose_name="Test name", max_length=200)

    # This doesn't work; tweak the admin formfield_for_foreignkey instead
    #def limit_file_choices(self):
        #return {'exercise': self.exercise}

    required_files = models.ManyToManyField('FileExerciseTestIncludeFile',
                                            verbose_name="files required by this test",
                                            #limit_choices_to=limit_file_choices,
                                            blank=True)
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "file exercise test"

class FileExerciseTestStage(models.Model):
    """A stage – a named sequence of commands to run in a file exercise test."""
    test = models.ForeignKey(FileExerciseTest)
    depends_on = models.ForeignKey('FileExerciseTestStage', null=True, blank=True) # TODO: limit_choices_to
    name = models.CharField(max_length=64) # Translate
    ordinal_number = models.PositiveSmallIntegerField() # TODO: Enforce min=1

    def __str__(self):
        return "%s: %02d - %s" % (self.test.name, self.ordinal_number, self.name)

    class Meta:
        unique_together = ('test', 'ordinal_number')
        ordering = ['ordinal_number']

class FileExerciseTestCommand(models.Model):
    """A command that shall be executed on the test machine."""
    stage = models.ForeignKey(FileExerciseTestStage)
    command_line = models.CharField(max_length=255)
    significant_stdout = models.BooleanField(verbose_name="Compare the generated stdout to reference",
                                             default=False,
                                             help_text="Determines whether the"\
                                             " standard output generated by "\
                                             "this command is compared to the "\
                                             "one generated by running this "\
                                             "command with the reference files.")
    significant_stderr = models.BooleanField(verbose_name="Compare the generated stderr to reference",
                                             default=False,
                                             help_text="Determines whether the standard errors generated by this command are compared to those generated by running this command with the reference files.")
    timeout = models.TimeField(default=default_timeout,
                               help_text="How long is the command allowed to run before termination?")
    POSIX_SIGNALS_CHOICES = (
        ('None', "Don't send any signals"),
        ('SIGINT', 'Interrupt signal (same as Ctrl-C)'),
        ('SIGTERM', 'Terminate signal'),
    )
    signal = models.CharField(max_length=8,default="None",choices=POSIX_SIGNALS_CHOICES,
                              help_text="Which POSIX signal shall be fired at the program?")
    input_text = models.TextField(verbose_name="Input fed to the command through STDIN",blank=True,
                                  help_text="What input shall be entered to the program's stdin upon execution?")
    return_value = models.IntegerField(verbose_name='Expected return value',blank=True,null=True)
    ordinal_number = models.PositiveSmallIntegerField() # TODO: Enforce min=1

    def __str__(self):
        return "%02d: %s" % (self.ordinal_number, self.command_line)

    class Meta:
        verbose_name = "command to run for the test"
        verbose_name_plural = "commands to run for the test"
        unique_together = ('stage', 'ordinal_number')
        ordering = ['ordinal_number']

class FileExerciseTestExpectedOutput(models.Model):
    """What kind of output is expected from the program?"""
    command = models.ForeignKey(FileExerciseTestCommand)
    correct = models.BooleanField(default=False)
    regexp = models.BooleanField(default=False)
    expected_answer = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    OUTPUT_TYPE_CHOICES = (
        ('STDOUT', 'Standard output (stdout)'),
        ('STDERR', 'Standard error (stderr)'),
    )
    output_type = models.CharField(max_length=7, default='STDOUT', choices=OUTPUT_TYPE_CHOICES)

class FileExerciseTestExpectedStdout(FileExerciseTestExpectedOutput):
    class Meta:
        verbose_name = "expected output"
        proxy = True

    def save(self, *args, **kwargs):
        self.output_type = "STDOUT"
        super(FileExerciseTestExpectedStdout, self).save(*args, **kwargs)

class FileExerciseTestExpectedStderr(FileExerciseTestExpectedOutput):
    class Meta:
        verbose_name = "expected error"
        proxy = True

    def save(self, *args, **kwargs):
        self.output_type = "STDERR"
        super(FileExerciseTestExpectedStderr, self).save(*args, **kwargs)

def get_testfile_path(instance, filename):
    return os.path.join(
        "%s_files" % (instance.exercise.name),
        "%s" % (filename)
    )

class FileExerciseTestIncludeFile(models.Model):
    """
    A file which an admin can include in an exercise's file pool for use in
    tests. For example, a reference program, expected output file or input file
    for the program.
    """
    exercise = models.ForeignKey(FileUploadExercise)
    name = models.CharField(verbose_name='File name during test',max_length=255)

    FILE_PURPOSE_CHOICES = (
        ('Files written into the test directory for reading', (
            ('INPUT', "Input file"),
        )),
        ('Files the program is expected to generate', (
            ('OUTPUT', "Expected output file"),
        )),
        ('Executable files', (
            ('REFERENCE', "Reference implementation"),
            ('INPUTGEN', "Input generator"),
            ('WRAPPER', "Wrapper for uploaded code"),
            ('TEST', "Unit test"),
        )),
    )
    # Default order: reference, inputgen, wrapper, test
    purpose = models.CharField(verbose_name='Used as',max_length=10,default="REFERENCE",choices=FILE_PURPOSE_CHOICES)

    FILE_OWNERSHIP_CHOICES = (
        ('OWNED', "Owned by the tested program"),
        ('NOT_OWNED', "Not owned by the tested program"),
    )
    chown_settings = models.CharField(verbose_name='File user ownership',max_length=10,default="OWNED",choices=FILE_OWNERSHIP_CHOICES)
    chgrp_settings = models.CharField(verbose_name='File group ownership',max_length=10,default="OWNED",choices=FILE_OWNERSHIP_CHOICES)
    chmod_settings = models.CharField(verbose_name='File access mode',max_length=10,default="rw-rw-rw-") # TODO: Create validator and own field type

    fileinfo = models.FileField(max_length=255, upload_to=get_testfile_path)

    def __str__(self):
        return "%s - %s" % (self.purpose, self.name)

    def get_filename(self):
        return os.path.basename(self.fileinfo.name)

    def get_file_contents(self):
        file_contents = None
        with open(self.fileinfo.path, 'rb') as f:
            file_contents = f.read()
        return file_contents

    class Meta:
        verbose_name = "included file"

# TODO: Create a superclass for exercise answer choices
## Answer models
@reversion.register()
class TextfieldExerciseAnswer(models.Model):
    exercise = models.ForeignKey(TextfieldExercise)
    correct = models.BooleanField(default=False)
    regexp = models.BooleanField(default=True)
    answer = models.TextField() # Translate
    hint = models.TextField(blank=True) # Translate
    comment = models.TextField(verbose_name='Extra comment given upon entering a matching answer',blank=True) # Translate

    def __str__(self):
        if len(self.answer) > 76:
            return self.answer[0:76] + " ..."
        else:
            return self.answer

    def save(self, *args, **kwargs):
        self.answer = self.answer.replace("\r", "")
        super(TextfieldExerciseAnswer, self).save(*args, **kwargs)

@reversion.register()
class MultipleChoiceExerciseAnswer(models.Model):
    exercise = models.ForeignKey(MultipleChoiceExercise)
    correct = models.BooleanField(default=False)
    answer = models.TextField() # Translate
    hint = models.TextField(blank=True) # Translate
    comment = models.TextField(verbose_name='Extra comment given upon selection of this answer',blank=True) # Translate

    def __str__(self):
        return self.answer

@reversion.register()
class CheckboxExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CheckboxExercise)
    correct = models.BooleanField(default=False)
    answer = models.TextField() # Translate
    hint = models.TextField(blank=True) # Translate
    comment = models.TextField(verbose_name='Extra comment given upon selection of this answer',blank=True) # Translate

    def __str__(self):
        return self.answer

@reversion.register()
class CodeInputExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CodeInputExercise)
    answer = models.TextField() # Translate

@reversion.register()
class CodeReplaceExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CodeReplaceExercise)
    answer = models.TextField() # Translate
    #replace_file = models.ForeignKey()
    replace_file = models.TextField() # DEBUG
    replace_line = models.PositiveIntegerField()

class Evaluation(models.Model):
    """Evaluation of a student's answer to an exercise."""
    correct = models.BooleanField(default=False)
    points = models.IntegerField(default=0)

    # Note: Evaluation should not be translated. The teacher should know which
    # language the student used and give an evaluation using that language.

    evaluation_date = models.DateTimeField(verbose_name='When was the answer evaluated', auto_now_add=True)
    evaluator = models.ForeignKey(User, verbose_name='Who evaluated the answer', blank=True, null=True)
    feedback = models.TextField(verbose_name='Feedback given by a teacher', blank=True)
    test_results = models.TextField(verbose_name='Test results in JSON', blank=True) # TODO: JSONField

## TODO: Should these actually be proxied like the exercise types?
class UserAnswer(models.Model):
    """Parent class for what users have given as their answers to different exercises."""
    instance = models.ForeignKey(CourseInstance)
    evaluation = models.OneToOneField(Evaluation, null=True, blank=True)
    revision = models.PositiveIntegerField() # The revision info is always required!
    user = models.ForeignKey(User)
    answer_date = models.DateTimeField(verbose_name='Date and time of when the user answered this exercise',
                                       auto_now_add=True)
    answerer_ip = models.GenericIPAddressField()

    # TODO: Think about an arrayfield for collaborators. Maybe have a group system, where
    # the users form groups based on usernames, after which those usernames can be added
    # in to the collaborators field when answering the exercise? Or some other policy –
    # the above mentioned could be too hard to use for spontaneous group formation...
    collaborators = models.TextField(verbose_name='Which users was this exercise answered with', blank=True, null=True)
    checked = models.BooleanField(verbose_name='This answer has been checked', default=False)
    draft = models.BooleanField(verbose_name='This answer is a draft', default=False)

# TODO: Put in UserFileUploadExerciseAnswer's manager?
def get_version(instance):
    return UserFileUploadExerciseAnswer.objects.filter(user=instance.answer.user,
                                                       exercise=instance.answer.exercise).count()

def get_answerfile_path(instance, filename):
    return os.path.join(
        "returnables",
        "%s" % (instance.answer.user.username),
        "%s" % (instance.answer.exercise.name),
        "%04d" % (get_version(instance)),
        "%s" % (filename)
    )

class FileUploadExerciseReturnFile(models.Model):
    """A file that a user returns for checking."""
    answer = models.ForeignKey('UserFileUploadExerciseAnswer')
    fileinfo = models.FileField(max_length=255, upload_to=get_answerfile_path)

    def filename(self):
        return os.path.basename(self.fileinfo.name)

    def get_type(self):
        try:
            mimetype = str(magic.from_file(self.fileinfo.path, mime=True), encoding="utf-8")
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

class UserFileUploadExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(FileUploadExercise)

    def __str__(self):
        return "Answer by %s" % (self.user.username)

    def get_returned_files_raw(self):
        file_objects = FileUploadExerciseReturnFile.objects.filter(answer=self)
        returned_files = {}
        for returned_file in file_objects:
            path = returned_file.fileinfo.path
            with open(path, 'rb') as f:
                contents = f.read()
                returned_files[returned_file.filename()] = contents
        return returned_files

    def get_returned_files(self):
        file_objects = FileUploadExerciseReturnFile.objects.filter(answer=self)
        returned_files = {}
        for returned_file in file_objects:
            path = returned_file.fileinfo.path
            with open(path, 'rb') as f:
                contents = f.read()
                type_info = returned_file.get_type()
                if not type_info[1]:
                    try:
                        lexer = pygments.lexers.guess_lexer_for_filename(path, contents)
                    except pygments.util.ClassNotFound:
                        pass
                    else:
                        contents = pygments.highlight(contents, lexer, pygments.formatters.HtmlFormatter(nowrap=True))
                returned_files[returned_file.filename()] = type_info + (contents,)
        return returned_files

class UserTextfieldExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(TextfieldExercise)
    given_answer = models.TextField()

    def __str__(self):
        return self.given_answer

class UserMultipleChoiceExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(MultipleChoiceExercise)
    chosen_answer = models.ForeignKey(MultipleChoiceExerciseAnswer)

    def __str__(self):
        return self.chosen_answer

    def is_correct(self):
        return chosen_answer.correct

class UserCheckboxExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(CheckboxExercise)
    chosen_answers = models.ManyToManyField(CheckboxExerciseAnswer)

    def __str__(self):
        return ", ".join(self.chosen_answers)

class CodeReplaceExerciseReplacement(models.Model):
    answer = models.ForeignKey('UserCodeReplaceExerciseAnswer')
    target = models.ForeignKey(CodeReplaceExerciseAnswer)
    replacement = models.TextField()

class UserCodeReplaceExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(CodeReplaceExercise)
    given_answer = models.TextField()

    def __str__(self):
        return given_answer

class InvalidAnswerException(Exception):
    """
    This exception is cast when an exercise answer cannot be processed.
    """
    pass
