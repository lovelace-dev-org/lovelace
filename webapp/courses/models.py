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

# TODO: Abstract the task model to allow "an answering entity" to give the answer, be it a group or a student

class Course(models.Model):
    """
    Describes the metadata for a course.
    """
    name = models.CharField(max_length=255)
    code = models.CharField(verbose_name="Course code",
                            help_text="Course code for e.g. universities",
                            max_length=64, blank=True, null=True)
    credits = models.DecimalField(verbose_name="Course credits",
                                  help_text="How many credits does the course"
                                  "yield on completion. (For e.g. universities",
                                  max_digits=6, decimal_places=2,
                                  blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    slug = models.CharField(max_length=255, db_index=True, unique=True)
    prerequisites = models.ManyToManyField('Course',
                                           verbose_name="Prerequisite courses",
                                           blank=True, null=True)

    # TODO: Move the fields below to instance
    frontpage = models.ForeignKey('LecturePage', blank=True,null=True) # TODO: Create one automatically!
    contents = models.ManyToManyField('ContentGraph', blank=True,null=True) # TODO: Rethink the content graph system!

    start_date = models.DateTimeField(verbose_name='Date and time on which the course begins',blank=True,null=True)
    end_date = models.DateTimeField(verbose_name='Date and time on which the course ends',blank=True,null=True)
    # TODO: Registration start and end dates for students!

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
    compulsory = models.BooleanField(verbose_name='Must be answered correctly before proceeding to next task', default=False)
    deadline = models.DateTimeField(verbose_name='The due date for completing this task',blank=True,null=True)
    publish_date = models.DateTimeField(verbose_name='When does this task become available',blank=True,null=True)
    scored = models.BooleanField(verbose_name='Does this task affect scoring', default=True)
    require_correct_embedded = models.BooleanField(verbose_name='Embedded exercises must be answered correctly in order to mark this item as correct',default=True)

    def __str__(self):
        if not self.content:
            return "No linked content yet"
        return self.content.short_name

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
    url_name = models.CharField(max_length=200,editable=False) # Use SlugField instead? rename to slug
    slug = models.CharField(max_length=255, db_index=True, unique=True)
    # TODO: Get rid of short_name
    short_name = models.CharField(max_length=32, help_text="The short name is used for referring this page on other pages")
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

    def _shortify_name(self):
        # duplicate page warning! what if two pages have the same [0:32]?
        return self.name[0:32]

    def get_url_name(self):
        """Creates a URL and HTML ID field friendly version of the name."""
        # TODO: HTML5 id accepts unicode. Only problematic characters:  ,.:;
        # TODO: Use mozilla/unicode-slugify
        # https://github.com/mozilla/unicode-slugify
        return re.sub(r"[^A-Za-z0-9_]", "_", self.name).lower()

    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()

        # TODO: Run through content parser
        #       - Check for & report errors (all errors on same notice)
        #       - Put into Redis cache
        #       - Automatically link embedded pages (create/update an
        #         EmbeddedContentLink object)
        super(ContentPage, self).save(*args, **kwargs)

    def __str__(self):
        return self.name

# TODO: Use the below models as Meta -> proxy = True
#       - override save(): automatically save content_type based on which kind
#         of lecture/exercise the object is
# TODO: Rename to Lecture
class LecturePage(ContentPage):
    """A single page for a lecture."""
    answerable = models.BooleanField(verbose_name="Need confirmation of reading this lecture",default=False)

    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(LecturePage, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "lecture page"

# TODO: Rename to Exercise
# TODO: Break the exercises into an exercises app
# TODO: Manually evaluated flag (good for final projects)
class TaskPage(ContentPage):
    """A single task."""
    question = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(TaskPage, self).save(*args, **kwargs)

class RadiobuttonTask(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(RadiobuttonTask, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "multiple choice exercise"

class CheckboxTask(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(CheckboxTask, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "checkbox exercise"

class TextfieldTask(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(TextfieldTask, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "text field exercise"

class FileUploadExercise(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(FileUploadExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "file upload exercise"

class CodeInputExercise(TaskPage):
    # TODO: A textfield exercise variant that's run like a file exercise (like in Viope)
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(CodeInputExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "code input exercise"

class CodeReplaceExercise(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(CodeReplaceExercise, self).save(*args, **kwargs)

    class Meta:
        verbose_name = "code replace exercise"

class Hint(models.Model):
    """
    A hint that is linked to an exercise and shown to the user under
    configurable conditions.
    """
    exercise = models.ForeignKey(TaskPage)
    hint = models.TextField(verbose_name="hint text")
    tries_to_unlock = models.IntegerField(default=0,
                                          verbose_name="number of tries to unlock this hint",
                                          help_text="Use 0 to show the hint immediately – before any answer attempts.")

    class Meta:
        verbose_name = "configurable hint"

## File exercise test related models
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
    # TODO: save()

class FileExerciseTestExpectedStderr(FileExerciseTestExpectedOutput):
    class Meta:
        verbose_name = "expected error"
        proxy = True
    # TODO: save()

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
            )
        ),
        ('Files the program is expected to generate', (
                ('OUTPUT', "Expected output file"),
            )
        ),
        ('Executable files', (
                ('REFERENCE', "Reference implementation"),
                ('INPUTGEN', "Input generator"),
                ('TEST', "Unit test"),
            )
        ),
    )
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
        return u"%s - %s" % (self.purpose, self.name)

    class Meta:
        verbose_name = "included file"

# TODO: Create a superclass for task answer choices
## Answer models
class TextfieldTaskAnswer(models.Model):
    task = models.ForeignKey(TextfieldTask)
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
        super(TextfieldTaskAnswer, self).save(*args, **kwargs)
 
class RadiobuttonTaskAnswer(models.Model):
    task = models.ForeignKey(RadiobuttonTask)
    correct = models.BooleanField(default=None)
    answer = models.TextField()
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)
    comment = models.TextField(verbose_name='Extra comment given upon selection of this answer',blank=True)

    def __str__(self):
        return self.answer

class CheckboxTaskAnswer(models.Model):
    task = models.ForeignKey(CheckboxTask)
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
            return u"Correct answer to (todo: task) by %s with %f points: %s" % (self.useranswer.user.username, self.points, self.feedback)
        else:
            return u"Incorrect answer to (todo: task) by %s with %f points: %s" % (self.useranswer.user.username, self.points, self.feedback)

class UserAnswer(models.Model):
    """Parent class for what users have given as their answers to different tasks."""
    evaluation = models.OneToOneField(Evaluation)
    user = models.ForeignKey(User)
    answer_date = models.DateTimeField(verbose_name='Date and time of when the user answered this task',
                                       auto_now_add=True)
    answerer_ip = models.GenericIPAddressField()

    collaborators = models.TextField(verbose_name='Which users was this task answered with', blank=True, null=True)
    checked = models.BooleanField(verbose_name='This answer has been checked', default=False)
    draft = models.BooleanField(verbose_name='This answer is a draft', default=False)

# TODO: Put in UserFileUploadExerciseAnswer's manager?
def get_version(instance):
    return UserFileUploadExerciseAnswer.objects.filter(user=instance.answer.user,
                                                       task=instance.answer.task).count()

def get_answerfile_path(instance, filename):
    return os.path.join(
        "returnables",
        "%s" % (instance.answer.user.username),
        "%s" % (instance.answer.task.name),
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
    task = models.ForeignKey(FileUploadExercise)

    def __str__(self):
        return u"Answer by %s" % (self.user.username)

class UserTextfieldTaskAnswer(UserAnswer):
    task = models.ForeignKey(TextfieldTask)
    given_answer = models.TextField()

    def __str__(self):
        #return u"Answer no. %04d: %s" % (self.answer_count, self.given_answer)
        return u"Answer by %s: %s" % (self.user.username, self.given_answer)

class UserRadiobuttonTaskAnswer(UserAnswer):
    task = models.ForeignKey(RadiobuttonTask)
    chosen_answer = models.ForeignKey(RadiobuttonTaskAnswer)

    def __str__(self):
        #return u"Answer no. %04d by %s: %s" % (self.answer_count, self.user.username, self.chosen_answer)
        return u"Answer by %s: %s" % (self.user.username, self.chosen_answer)

    def is_correct(self):
        return chosen_answer.correct

class UserCheckboxTaskAnswer(UserAnswer):
    task = models.ForeignKey(CheckboxTask)
    chosen_answers = models.ManyToManyField(CheckboxTaskAnswer)

    def __str__(self):
        #return u"Answer no. %04d: %s" % (self.answer_count, ", ".join(self.chosen_answers))
        return u"Answer by %s: %s" % (self.user.username, ", ".join(self.chosen_answers))

class UserLecturePageAnswer(UserAnswer):
    task = models.ForeignKey(LecturePage)
    answered = models.BooleanField(LecturePage, default=None)
    
    def __str__(self):
        return u"Answered by %s." % (self.user.username)

