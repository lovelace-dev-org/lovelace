from django.db import models
from django.contrib.auth.models import User

#from courses.models import ContentPage # prevent circular import

## Feedback models
class ContentFeedbackQuestion(models.Model):
    """A five star feedback that can be linked to any content."""
    question = models.CharField(verbose_name="Question",max_length=100)

    def __str__(self):
        return self.question

class ContentFeedbackUserAnswer(models.Model):
    user = models.ForeignKey(User)                          # The user who has given this feedback
    content = models.ForeignKey('courses.ContentPage')      # The content on which this feedback was given
    question = models.ForeignKey(ContentFeedbackQuestion)   # The feedback question this feedback answers
    rating = models.PositiveSmallIntegerField()
