from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save

# http://stackoverflow.com/questions/44109/extending-the-user-model-with-custom-fields-in-django
class UserProfile(models.Model):
    """The user profile."""
    user = models.OneToOneField(User)
    student_id = models.IntegerField()

    def __unicode__(self):
        return "%s's profile" % self.user

def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, created = UserProfile.objects.get_or_create(user=instance)

post_save.connect(create_user_profile, sender=User)

class Course(models.Model):
    """A single course in the system.

    A course consists of shared content, i.e. lectures, tasks etc.
    but is represented to users via an Incarnation.

    A course also holds its own set of files (source code, images, pdfs, etc.)
    with their metadata.

    An Incarnation has a specified subset of the shared course content
    and a subset of users in the whole system.

    A user or a group can be in charge of a course."""

    name = models.CharField(max_length=200)

    def __unicode__(self):
        return self.name
    
class Incarnation(models.Model):
    """An incarnation of a course.

    Saves data on which users are partaking and which course material is
    available on this specific instance of a course.

    A user or a group can be in charge of a course incarnation."""
    
    course = models.ForeignKey(Course)
    frozen = models.BooleanField() # If no changes are possible to this instance of the course
    start_date = models.DateTimeField('course begin date')
    end_date = models.DateTimeField('course end date')

    def __unicode__(self):
        return str(self.start_date)

class File(models.Model):
    """Metadata of a file that a user has uploaded."""

    course = models.ForeignKey(Course)
    uploader = models.ForeignKey(User)

    date_uploaded = models.DateTimeField('date uploaded')
    name = models.CharField(max_length=200)
    typeinfo = models.CharField(max_length=200)
    fileinfo = models.FileField(upload_to='%s/files' % course.name) # TODO: Can this cause problems if course.name has /?
    # https://docs.djangoproject.com/en/dev/ref/models/fields/#filefield

class ContentGraph(models.Model):
    """Defines the tree (or the graph) of the course content."""
    incarnation = models.ForeignKey(Incarnation)

class Responsible(models.Model):
    """A user or a group that has been assigned as responsible for a course, course incarnation or some specific material."""
    pass

class ContentPage(models.Model):
    """A single content containing page of a course.

    May be a part of a course incarnation graph."""
    content = models.TextField()

class LecturePage(ContentPage):
    """A single page from a lecture."""
    pass

class TaskPage(ContentPage):
    """A single task."""
    pass

class RadiobuttonTask(TaskPage):
    pass

class CheckboxTask(TaskPage):
    pass

class TextfieldTask(TaskPage):
    pass

class FileTask(TaskPage):
    pass

class FileTaskTest(models.Model):
    pass

