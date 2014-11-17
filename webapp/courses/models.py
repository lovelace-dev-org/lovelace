"""Django database models for courses."""
# TODO: Refactor into multiple apps
# TODO: Serious effort to normalize the db!
# TODO: Profile the app and add relevant indexes!

import datetime
import re
import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.urlresolvers import reverse

import slugify

from feedback.models import ContentFeedbackQuestion

# TODO: Extend the registration system to allow users to enter the profile data!
class UserProfile(models.Model):
    """User profile, which extends the Django's User model."""
    # For more information, see:
    # https://docs.djangoproject.com/en/dev/topics/auth/#storing-additional-information-about-users
    # http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
    user = models.OneToOneField(User)
    student_id = models.IntegerField(verbose_name='Student number', blank=True, null=True)
    study_program = models.CharField(verbose_name='Study program', max_length=80, blank=True, null=True)

    def __str__(self):
        return "%s's profile" % self.user

    def save(self, *args, **kwargs):
        # To prevent 'column user_id is not unique' error from creating a new user in admin interface
        # http://stackoverflow.com/a/2813728
        try:
            existing = UserProfile.objects.get(user=self.user)
            self.id = existing.id
        except UserProfile.DoesNotExist:
            pass
        models.Model.save(self, *args, **kwargs)

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User, dispatch_uid="create_user_profile_raippa")

# TODO: A user group system for allowing users to form groups
# - max users / group

# TODO: Abstract the exercise model to allow "an answering entity" to give the answer, be it a group or a student

class Course(models.Model):
    """
    Describes the metadata for a course.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(verbose_name="Course code",
                            help_text="Course code, for e.g. universities",
                            max_length=64, blank=True, null=True)
    credits = models.DecimalField(verbose_name="Course credits",
                                  help_text="How many credits does the course "
                                  "yield on completion, for e.g. universities",
                                  max_digits=6, decimal_places=2,
                                  blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    slug = models.CharField(max_length=255, db_index=True, unique=True)
    prerequisites = models.ManyToManyField('Course',
                                           verbose_name="Prerequisite courses",
                                           blank=True, null=True)

    # TODO: Move the fields below to instance
    frontpage = models.ForeignKey('Lecture', blank=True,null=True) # TODO: Create one automatically!
    contents = models.ManyToManyField('ContentGraph', blank=True,null=True) # TODO: Rethink the content graph system!

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        # TODO: Ensure uniqueness!
        return slugify.slugify(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        super(Course, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

# TODO: Reintroduce the incarnation system and make it transparent to users
class CourseInstance(models.Model):
    """
    A running instance of a course. Contains details about the start and end
    dates of the course.
    """
    name = models.CharField(max_length=255)
    course = models.ForeignKey('Course')
    start_date = models.DateTimeField(verbose_name='Date and time on which the course begins',blank=True,null=True)
    end_date = models.DateTimeField(verbose_name='Date and time on which the course ends',blank=True,null=True)
    #link the content graph nodes to this instead

class ContentGraph(models.Model):
    """A node in the course tree/graph. Links content into a course."""
    # TODO: Rethink the content graph system!
    # TODO: Take embedded content into account! (Maybe: automatically make content nodes from embedded content)
    # TODO: "Allow answering after deadline has passed" flag.
    parentnode = models.ForeignKey('self', null=True, blank=True)
    content = models.ForeignKey('ContentPage', null=True, blank=True)
    responsible = models.ManyToManyField(User,blank=True,null=True)
    compulsory = models.BooleanField(verbose_name='Must be answered correctly before proceeding to next exercise', default=False)
    deadline = models.DateTimeField(verbose_name='The due date for completing this exercise',blank=True,null=True)
    publish_date = models.DateTimeField(verbose_name='When does this exercise become available',blank=True,null=True)
    scored = models.BooleanField(verbose_name='Does this exercise affect scoring', default=True)
    require_correct_embedded = models.BooleanField(verbose_name='Embedded exercises must be answered correctly in order to mark this item as correct',default=True)

    def __str__(self):
        if not self.content:
            return "No linked content yet"
        return self.content.slug

    class Meta:
        verbose_name = "content to course link"
        verbose_name_plural = "content to course links"

class EmbeddedContentLink(models.Model):
    """
    Automatically generated link from content to other content - based on
    content pages embedded in other content pages.
    """
    # TODO: Um... rethink relations
    page = models.ForeignKey('ContentPage', related_name='embedded_page_link')
    embedded_pages = models.ManyToManyField('ContentPage', related_name='parent_page_links')

def get_file_upload_path(instance, filename):
    return os.path.join("files", "%s" % (filename))

class File(models.Model):
    """Metadata of an embedded or attached file that an admin has uploaded."""
    uploader = models.ForeignKey(User) # TODO: Make the uploading user the default and don't allow it to change
    name = models.CharField(verbose_name='Name for reference in content',max_length=200,unique=True)
    date_uploaded = models.DateTimeField(verbose_name='date uploaded', auto_now_add=True)
    typeinfo = models.CharField(max_length=200)
    fileinfo = models.FileField(max_length=255, upload_to=get_file_upload_path)

    def __str__(self):
        return self.name

def get_image_upload_path(instance, filename):
    return os.path.join("images", "%s" % (filename))

class Image(models.Model):
    """Image"""
    uploader = models.ForeignKey(User)
    name = models.CharField(verbose_name='Name for reference in content',max_length=200,unique=True)
    date_uploaded = models.DateTimeField(verbose_name='date uploaded', auto_now_add=True)
    description = models.CharField(max_length=500)
    fileinfo = models.ImageField(upload_to=get_image_upload_path)

    def __str__(self):
        return self.name

class Video(models.Model):
    """Youtube link for embedded videos"""
    name = models.CharField(max_length=200)
    link = models.URLField()
    uploader = models.ForeignKey(User)

    def __str__(self):
        return self.name

## Time reservation and event calendar system
class Calendar(models.Model):
    """A multi purpose calendar for course events markups, time reservations etc."""
    name = models.CharField(verbose_name='Name for reference in content',max_length=200,unique=True)

    def __str__(self):
        return self.name

class CalendarDate(models.Model):
    """A single date on a calendar."""
    calendar = models.ForeignKey(Calendar)
    event_name = models.CharField(verbose_name='Name of the event', max_length=200)
    event_description = models.CharField(verbose_name='Description', max_length=200, blank=True, null=True)
    start_time = models.DateTimeField(verbose_name='Starts at')
    end_time = models.DateTimeField(verbose_name='Ends at')
    reservable_slots = models.IntegerField(verbose_name='Amount of reservable slots')

    def __str__(self):
        return self.event_name

class CalendarReservation(models.Model):
    """A single user made reservation on a calendar date."""
    calendar_date = models.ForeignKey(CalendarDate)
    user = models.ForeignKey(User)

## Content management
class ContentPage(models.Model):
    """
    A single content containing page of a course.
    The used content pages (Lecture and Exercise) and their
    child classes all inherit from this class.
    """
    name = models.CharField(max_length=255, help_text="The full name of this page")
    slug = models.CharField(max_length=255, db_index=True, unique=True)
    content = models.TextField(verbose_name="Page content body", blank=True, null=True)
    default_points = models.IntegerField(blank=True, null=True,
                                         help_text="The default points a user can gain by finishing this exercise correctly")
    access_count = models.PositiveIntegerField(editable=False,blank=True,null=True)
    tags = models.TextField(blank=True,null=True)
    
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

    feedback_questions = models.ManyToManyField(ContentFeedbackQuestion, blank=True, null=True)

    def get_admin_change_url(self):
        adminized_type = self.content_type.replace("_", "").lower()
        return reverse("admin:courses_%s_change" % (adminized_type), args=(self.id,))

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        # TODO: Ensure uniqueness!
        return slugify.slugify(self.name)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        # TODO: Run through content parser
        #       - Check for & report errors (all errors on same notice)
        #       - Put into Redis cache
        #       - Automatically link embedded pages (create/update an
        #         EmbeddedContentLink object)
        super(ContentPage, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

# TODO: Use the below models as Meta -> proxy = True
class Lecture(ContentPage):
    """A single page for a lecture."""
    answerable = models.BooleanField(verbose_name="Need confirmation of reading this lecture",default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)
        
        self.content_type = "LECTURE"
        super(Lecture, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "lecture page"

# TODO: Break the exercises into an exercises app
class Exercise(ContentPage):
    """A single exercise."""
    question = models.TextField(blank=True, null=True)
    manually_evaluated = models.BooleanField(verbose_name="This exercise is evaluated by hand", default=False)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)
        super(Exercise, self).save(*args, **kwargs)

class MultipleChoiceExercise(Exercise):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        self.content_type = "MULTIPLE_CHOICE_EXERCISE"
        super(MultipleChoiceExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "multiple choice exercise"

class CheckboxExercise(Exercise):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        self.content_type = "CHECKBOX_EXERCISE"
        super(CheckboxExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "checkbox exercise"

class TextfieldExercise(Exercise):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        self.content_type = "TEXTFIELD_EXERCISE"
        super(TextfieldExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "text field exercise"

class FileUploadExercise(Exercise):
    # TODO: A field for restricting uploadable file names (e.g. by extension, like .py)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        self.content_type = "FILE_UPLOAD_EXERCISE"
        super(FileUploadExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "file upload exercise"

class CodeInputExercise(Exercise):
    # TODO: A textfield exercise variant that's run like a file exercise (like in Viope)
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        self.content_type = "CODE_INPUT_EXERCISE"
        super(CodeInputExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "code input exercise"

class CodeReplaceExercise(Exercise):
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        self.content_type = "CODE_REPLACE_EXERCISE"
        super(CodeReplaceExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "code replace exercise"

# TODO: Code exercise that is ranked (against others/by some known scale/etc.)
# Inspiration:
# - coding competitions (correctness + timing/cpu cycle restrictions)
# - artificial intelligence course (competing othello AI algorithms)
# - pattern recognition and neural networks course (performance of an pattern
#   recognition algorithm)
#class RankedCodeExercise(Exercise):
    #def save(self, *args, **kwargs):
        #if not self.slug:
            #self.slug = self.get_url_name()
        #else:
            #self.slug = slugify.slugify(self.slug)
#
        #self.content_type = "RANKED_CODE_EXERCISE"
        #super(RankedCodeExercise, self).save(*args, **kwargs)

# TODO: Group code exercise. All group members must return their own files!
# Inspiration:
# - computer networks I course

class Hint(models.Model):
    """
    A hint that is linked to an exercise and shown to the user under
    configurable conditions.
    """
    exercise = models.ForeignKey(Exercise)
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
    
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "file exercise test"

class FileExerciseTestStage(models.Model):
    """A stage – a named sequence of commands to run in a file exercise test."""
    test = models.ForeignKey(FileExerciseTest)
    depends_on = models.ForeignKey('FileExerciseTestStage', null=True, blank=True) # TODO: limit_choices_to
    name = models.CharField(max_length=64)
    ordinal_number = models.PositiveSmallIntegerField() # TODO: Enforce min=1

    def __str__(self):
        return self.name

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
        return "%s" % (self.command_line)

    class Meta:
        verbose_name = "command to run for the test"
        verbose_name_plural = "commands to run for the test"
        unique_together = ('stage', 'ordinal_number')
        ordering = ['ordinal_number']

class FileExerciseTestExpectedOutput(models.Model):
    """What kind of output is expected from the program?"""
    command = models.ForeignKey(FileExerciseTestCommand)
    correct = models.BooleanField(default=None)
    regexp = models.BooleanField(default=None)
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
        "%s_files" % (instance.test.name),
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

    class Meta:
        verbose_name = "included file"

# TODO: Create a superclass for exercise answer choices
## Answer models
class TextfieldExerciseAnswer(models.Model):
    exercise = models.ForeignKey(TextfieldExercise)
    correct = models.BooleanField(default=None)
    regexp = models.BooleanField(default=None)
    answer = models.TextField()
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)
    comment = models.TextField(verbose_name='Extra comment given upon entering a matching answer',blank=True)

    def __str__(self):
        if len(self.answer) > 76:
            return self.answer[0:76] + " ..."
        else:
            return self.answer

    def save(self, *args, **kwargs):
        self.answer = self.answer.replace("\r\n", "\n").replace("\n\r", "\n")
        super(TextfieldExerciseAnswer, self).save(*args, **kwargs)
 
class MultipleChoiceExerciseAnswer(models.Model):
    exercise = models.ForeignKey(MultipleChoiceExercise)
    correct = models.BooleanField(default=None)
    answer = models.TextField()
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)
    comment = models.TextField(verbose_name='Extra comment given upon selection of this answer',blank=True)

    def __str__(self):
        return self.answer

class CheckboxExerciseAnswer(models.Model):
    exercise = models.ForeignKey(CheckboxExercise)
    correct = models.BooleanField(default=None)
    answer = models.TextField()
    hint = models.TextField(blank=True)    
    videohint = models.ForeignKey(Video,blank=True,null=True)  
    comment = models.TextField(verbose_name='Extra comment given upon selection of this answer',blank=True)

    def __str__(self):
        return self.answer

class Evaluation(models.Model):
    """Evaluation of a student's exercise answer."""
    correct = models.BooleanField(default=None)
    points = models.FloatField(blank=True)
    feedback = models.TextField(verbose_name='Feedback given by a teacher',blank=True)

    def __str__(self):
        if self.correct:
            return "Correct answer to (todo: exercise) by %s with %f points: %s" % (self.useranswer.user.username, self.points, self.feedback)
        else:
            return "Incorrect answer to (todo: exercise) by %s with %f points: %s" % (self.useranswer.user.username, self.points, self.feedback)

class UserAnswer(models.Model):
    """Parent class for what users have given as their answers to different exercises."""
    evaluation = models.OneToOneField(Evaluation)
    user = models.ForeignKey(User)
    answer_date = models.DateTimeField(verbose_name='Date and time of when the user answered this exercise',
                                       auto_now_add=True)
    answerer_ip = models.GenericIPAddressField()

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

class UserFileUploadExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(FileUploadExercise)

    def __str__(self):
        return "Answer by %s" % (self.user.username)

class UserTextfieldExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(TextfieldExercise)
    given_answer = models.TextField()

    def __str__(self):
        #return "Answer no. %04d: %s" % (self.answer_count, self.given_answer)
        return "Answer by %s: %s" % (self.user.username, self.given_answer)

class UserMultipleChoiceExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(MultipleChoiceExercise)
    chosen_answer = models.ForeignKey(MultipleChoiceExerciseAnswer)

    def __str__(self):
        #return "Answer no. %04d by %s: %s" % (self.answer_count, self.user.username, self.chosen_answer)
        return "Answer by %s: %s" % (self.user.username, self.chosen_answer)

    def is_correct(self):
        return chosen_answer.correct

class UserCheckboxExerciseAnswer(UserAnswer):
    exercise = models.ForeignKey(CheckboxExercise)
    chosen_answers = models.ManyToManyField(CheckboxExerciseAnswer)

    def __str__(self):
        #return "Answer no. %04d: %s" % (self.answer_count, ", ".join(self.chosen_answers))
        return "Answer by %s: %s" % (self.user.username, ", ".join(self.chosen_answers))

class UserLecturePageAnswer(UserAnswer):
    exercise = models.ForeignKey(Lecture)
    answered = models.BooleanField(default=None)
    
    def __str__(self):
        return "Answered by %s." % (self.user.username)

