# -*- coding: utf-8 -*-
"""Django database models for RAIPPA courses."""

import datetime
import re
import os

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# TODO: Extend the user profiles!
# http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
#class UserProfile(models.Model):
#    """The user profile."""
#    user = models.OneToOneField(User)
#    student_id = models.IntegerField()
#
#    def __unicode__(self):
#        return "%s's profile" % self.user

#def create_user_profile(sender, instance, created, **kwargs):
#    if created:
#        profile, created = UserProfile.objects.get_or_create(user=instance)

#post_save.connect(create_user_profile, sender=User)

# TODO: A user group system for allowing users to form groups
# - max users / group

# TODO: Abstract the task model to allow "an answering entity" to give the answer, be it a group or a student

class Training(models.Model):
    """A single course in the system.

    A course consists of shared content, i.e. lectures, tasks etc.
    but is represented to users via an Incarnation.

    A course also holds its own set of files (source code, images, pdfs, etc.)
    with their metadata.

    A user or a group can be in charge of a course."""
    name = models.CharField(max_length=200)
    frontpage = models.ForeignKey('LecturePage', blank=True,null=True)
    contents = models.ManyToManyField('ContentGraph', blank=True,null=True)
    start_date = models.DateTimeField('Date and time after which the training is available',blank=True,null=True)
    end_date = models.DateTimeField('Date and time on which the training becomes obsolete',blank=True,null=True)
    responsible = models.ManyToManyField(User,related_name="responsiblefor",blank=True,null=True)
    staff = models.ManyToManyField(User,blank=True,null=True,related_name="staffing")
    students = models.ManyToManyField(User,blank=True,null=True,related_name="studentin")

    def __unicode__(self):
        return self.name

class ContentGraph(models.Model):
    parentnode = models.ForeignKey('self', null=True, blank=True)
    content = models.ForeignKey('ContentPage', null=True, blank=True)
    responsible = models.ManyToManyField(User,blank=True,null=True)
    compulsory = models.BooleanField('Must be answered correctly before proceeding to next task', default=True)
    deadline = models.DateTimeField('The due date for completing this task',blank=True,null=True)
    # TODO: Add this when next database layout comes
    #publish_date = models.DateTimeField('When does this task become available',blank=True,null=True)

    def __unicode__(self):
        return self.content.short_name

def get_file_upload_path(instance, filename):
    return os.path.join("files", "%s" % (filename))

class File(models.Model):
    """Metadata of an embedded or attached file that an admin has uploaded."""

    uploader = models.ForeignKey(User)

    date_uploaded = models.DateTimeField('date uploaded')
    name = models.CharField('Name for reference in content',max_length=200) # TODO: ,unique=True)
    typeinfo = models.CharField(max_length=200)
    fileinfo = models.FileField(upload_to=get_file_upload_path)

    def __unicode__(self):
        return self.name

def get_image_upload_path(instance, filename):
    return os.path.join("images", "%s" % (filename))

class Image(models.Model):
    """Image"""
    uploader = models.ForeignKey(User)
    name = models.CharField('Name for reference in content',max_length=200) # TODO: ,unique=True)
    date_uploaded = models.DateTimeField('date uploaded')
    description = models.CharField(max_length=500)
    fileinfo = models.ImageField(upload_to=get_image_upload_path)

    def __unicode__(self):
        return self.name

class Video(models.Model):
    """Youtube link for embedded videos"""
    name = models.CharField(max_length=200)
    link = models.URLField()
    uploader = models.ForeignKey(User)

    def __unicode__(self):
        return self.name

# TODO: Page embeddable calendar for, e.g., reserving review times
#class Calendar(models.Model):
#    """A multi purpose calendar for course events markups, time reservations etc."""
#    name = models.CharField('Name for reference in content',max_length=200,unique=True)

class ContentPage(models.Model):
    """A single content containing page of a course.
    The other content pages (LecturePage and TaskPage) and their
    child classes (RadiobuttonTask, CheckboxTask, TextfieldTask and FileTask)
    all inherit from this class.

    May be a part of a course incarnation graph."""
    name = models.CharField(max_length=200)
    url_name = models.CharField(max_length=200,editable=False) #,default=get_url_name) # Use SlugField instead?
    short_name = models.CharField(max_length=32) #, default=_shortify_name)
    content = models.TextField(blank=True,null=True)
    maxpoints = models.IntegerField(blank=True,null=True)
    # TODO: Add this when next database layout comes
    #access_count = models.IntegerField(editable=False)
    #tags = models.TextField(blank=True,null=True)
    #require_correct_embedded_tasks = models.BooleanField('If the page has embedded tasks, they must be answered correctly to make this task correct',default=True)

    def _shortify_name(self):
        return self.name[0:32]

    def get_url_name(self):
        """Creates an URL and HTML ID field friendly version of the name."""
        return re.sub(r"[^A-Za-z0-9_]", "_", self.name).lower()

    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(ContentPage, self).save(*args, **kwargs)

    def __unicode__(self):
        return self.name

class LecturePage(ContentPage):
    """A single page from a lecture."""
    # TODO: Add this when the next database layout comes
    #answerable = models.BooleanField("Do the users need to confirm they've read this lecture",default=False)
    # TODO: Add a lecturepageuseranswer model for this!

    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(LecturePage, self).save(*args, **kwargs)

class TaskPage(ContentPage):
    """A single task."""
    question = models.TextField()

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

class CheckboxTask(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(CheckboxTask, self).save(*args, **kwargs)

class TextfieldTask(TaskPage):
    # TODO: Create a Textfield task variant that's run like a file task! (like in Viope)
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(TextfieldTask, self).save(*args, **kwargs)

class FileTask(TaskPage):
    def save(self, *args, **kwargs):
        self.url_name = self.get_url_name()
        if not self.short_name:
            self.short_name = self._shortify_name()
        super(FileTask, self).save(*args, **kwargs)

class FileTaskTest(models.Model):
    task = models.ForeignKey(FileTask)
    name = models.CharField("Test name",max_length=200)
    timeout = models.TimeField(default=datetime.time(0,0,5))                  # How long is the test allowed to run before sending a KILL signal?
    POSIX_SIGNALS_CHOICES = (
        ('None', "Don't send any signals"),
        ('SIGINT', 'Interrupt signal (same as Ctrl-C)'),
    )
    signals = models.CharField(max_length=7,default="None",choices=POSIX_SIGNALS_CHOICES) # What POSIX signals shall be fired at the program?
    inputs = models.TextField("Input given to the main command through STDIN",blank=True) # What input shall be entered to the program's stdin upon execution?
    # TODO: Add this at the next database upgrade
    #retval = models.IntegerField('Expected return value',blank=True,null=True)

    def __unicode__(self):
        return self.name

class FileTaskTestCommand(models.Model):
    """A command that shall be executed on the test machine."""
    test = models.ForeignKey(FileTaskTest)
    command_line = models.CharField(max_length=500)
    main_command = models.BooleanField() # Is this the command which the inputs are entered into and signals are fired at?

class FileTaskTestExpectedOutput(models.Model):
    """What kind of output is expected from the program's stdout?"""
    test = models.ForeignKey(FileTaskTest)
    correct = models.BooleanField()
    regexp = models.BooleanField()
    expected_answer = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)

class FileTaskTestExpectedError(models.Model):
    """What kind of output is expected from the program's stderr?"""
    test = models.ForeignKey(FileTaskTest)
    correct = models.BooleanField()
    regexp = models.BooleanField()
    expected_answer = models.TextField(blank=True)
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)

def get_testfile_path(instance, filename):
    return os.path.join(
        "%s_files" % (instance.test.name),
        "%s" % (filename)
    )

class FileTaskTestIncludeFile(models.Model):
    """File which an admin can include to the test. For example, a reference program, expected output file or input file for the program."""
    test = models.ForeignKey(FileTaskTest)
    name = models.CharField(max_length=200)

    FILE_PURPOSE_CHOICES = (
        ('Files given to the program for reading', (
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
    purpose = models.CharField('Used as',max_length=10,default="REFERENCE",choices=FILE_PURPOSE_CHOICES)

    FILE_OWNERSHIP_CHOICES = (
        ('OWNED', "Owned by the tested program"),
        ('NOT_OWNED', "Now owned by the tested program"),
    )
    # TODO: Add this at the next database upgrade
    #chown_settings = models.CharField('File user ownership',max_length=10,default="OWNED",choices=FILE_OWNERSHIP_CHOICES)
    #chgrp_settings = models.CharField('File group ownership',max_length=10,default="OWNED",choices=FILE_OWNERSHIP_CHOICES)
    #chmod_settings = models.CharField('File access mode',max_length=10,default="rw-rw-rw-") # TODO: Create validator and own field type

    fileinfo = models.FileField(upload_to=get_testfile_path)

class TextfieldTaskAnswer(models.Model):
    task = models.ForeignKey(TextfieldTask)
    correct = models.BooleanField()
    regexp = models.BooleanField()
    answer = models.TextField()
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)
    # TODO: Add this at the next database upgrade
    #comment = models.TextField('Extra comment given upon selection of this answer',blank=True)

    def __unicode__(self):
        if len(self.answer) > 80:
            return self.answer[0:80] + u" ..."
        else:
            return self.answer

    def save(self, *args, **kwargs):
        self.answer = self.answer.replace("\r\n", "\n").replace("\n\r", "\n")
        super(TextfieldTaskAnswer, self).save(*args, **kwargs)
 
class RadiobuttonTaskAnswer(models.Model):
    task = models.ForeignKey(RadiobuttonTask)
    correct = models.BooleanField()
    answer = models.TextField()
    hint = models.TextField(blank=True)
    videohint = models.ForeignKey(Video,blank=True,null=True)
    # TODO: Add this at the next database upgrade
    #comment = models.TextField('Extra comment given upon selection of this answer',blank=True)

    def __unicode__(self):
        return self.answer

class CheckboxTaskAnswer(models.Model):
    task = models.ForeignKey(CheckboxTask)
    correct = models.BooleanField()
    answer = models.TextField()
    hint = models.TextField(blank=True)    
    videohint = models.ForeignKey(Video,blank=True,null=True)  
    # TODO: Add this at the next database upgrade
    #comment = models.TextField('Extra comment given upon selection of this answer',blank=True)

    def __unicode__(self):
        return self.answer

class Evaluation(models.Model):
    """Evaluation of training item performance"""
    points = models.FloatField()
    feedback = models.CharField('Feedback given by a teacher',max_length=2000,blank=True)
    
class UserAnswer(models.Model):
    """Parent class for what users have given as their answers to different tasks."""
    evaluation = models.OneToOneField(Evaluation) # A single answer is always linked to a single evaluation
    user = models.ForeignKey(User)                # Whose answer is this?
    answer_date = models.DateTimeField('Date and time of when the user answered this task')
    # TODO: Add this in next database upgrade!
    # collaborators = models.TextField('Which users was this task answered with', blank=True, null=True)

class FileTaskReturnable(models.Model):
    run_time = models.TimeField()
    output = models.TextField()
    errors = models.TextField()
    # TODO: Add this in the next database upgrade!
    # retval = models.IntegerField()

def get_version(instance):
    return UserFileTaskAnswer.objects.filter(user=instance.returnable.userfiletaskanswer.user,
                                             task=instance.returnable.userfiletaskanswer.task).count()

def get_answerfile_path(instance, filename):
    return os.path.join(
        "returnables",
        "%s" % (instance.returnable.userfiletaskanswer.user.username),
        "%s" % (instance.returnable.userfiletaskanswer.task.name),
        "%04d" % (get_version(instance)),
        "%s" % (filename)
    )

class FileTaskReturnFile(models.Model):
    """File that a user returns for checking."""
    returnable = models.ForeignKey(FileTaskReturnable)
    fileinfo = models.FileField(upload_to=get_answerfile_path)

    def filename(self):
        return os.path.basename(self.fileinfo.name)

class UserFileTaskAnswer(UserAnswer):
    task = models.ForeignKey(FileTask)
    returnable = models.OneToOneField(FileTaskReturnable)

    def __unicode__(self):
        #return u"Answer no. %04d: %s" % (self.answer_count, self.returnable)
        return u"Answer by %s: %s" % (self.user.username, self.returnable.output)

class UserTextfieldTaskAnswer(UserAnswer):
    task = models.ForeignKey(TextfieldTask)
    given_answer = models.TextField()

    def __unicode__(self):
        #return u"Answer no. %04d: %s" % (self.answer_count, self.given_answer)
        return u"Answer by %s: %s" % (self.user.username, self.given_answer)

class UserRadiobuttonTaskAnswer(UserAnswer):
    task = models.ForeignKey(RadiobuttonTask)
    chosen_answer = models.ForeignKey(RadiobuttonTaskAnswer)

    def __unicode__(self):
        #return u"Answer no. %04d by %s: %s" % (self.answer_count, self.user.username, self.chosen_answer)
        return u"Answer by %s: %s" % (self.user.username, self.chosen_answer)

    def is_correct(self):
        return chosen_answer.correct

class UserCheckboxTaskAnswer(UserAnswer):
    task = models.ForeignKey(CheckboxTask)
    chosen_answers = models.ManyToManyField(CheckboxTaskAnswer)

    def __unicode__(self):
        #return u"Answer no. %04d: %s" % (self.answer_count, ", ".join(self.chosen_answers))
        return u"Answer by %s: %s" % (self.user.username, ", ".join(self.chosen_answers))
    
