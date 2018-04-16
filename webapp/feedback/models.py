from django.utils.text import slugify
from django.db import models
from django.contrib.auth.models import User
import django.conf

#from courses.models import ContentPage # prevent circular import

## Feedback models 

QUESTION_TYPE_CHOICES = (
    ("THUMB_FEEDBACK", "Thumb feedback"),
    ("STAR_FEEDBACK", "Star feedback"),
    ("MULTIPLE_CHOICE_FEEDBACK", "Multiple choice feedback"),
    ("TEXTFIELD_FEEDBACK", "Textfield feedback"),
)

class ContentFeedbackQuestion(models.Model):
    """A feedback that can be linked to any content."""
    question = models.CharField(verbose_name="Question", max_length=100)
    question_type = models.CharField(max_length=28, default="TEXTFIELD_FEEDBACK", choices=QUESTION_TYPE_CHOICES)
    slug = models.SlugField(max_length=255, db_index=True, unique=True, allow_unicode=True)
    
    def __str__(self):
        return self.question

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        # TODO: Ensure uniqueness!
        default_lang = django.conf.settings.LANGUAGE_CODE
        return slugify(getattr(self, "question_{}".format(default_lang)), allow_unicode=True)
    
    def get_type_object(self):
        """Returns the actual type object of the question object that is the child of ContentFeedbackQuestion."""
        TYPE_MODELS = {
            "THUMB_FEEDBACK" : ThumbFeedbackQuestion,
            "STAR_FEEDBACK" : StarFeedbackQuestion,
            "MULTIPLE_CHOICE_FEEDBACK": MultipleChoiceFeedbackQuestion,
            "TEXTFIELD_FEEDBACK" : TextfieldFeedbackQuestion,
        }
        return TYPE_MODELS[self.question_type].objects.get(id=self.id)

    def get_answer_model(self):
        """Returns the corresponding answer model of the question object that is the child of ContentFeedbackQuestion."""
        ANSWER_MODELS = {
            "THUMB_FEEDBACK" : ThumbFeedbackUserAnswer,
            "STAR_FEEDBACK" : StarFeedbackUserAnswer,
            "MULTIPLE_CHOICE_FEEDBACK": MultipleChoiceFeedbackUserAnswer,
            "TEXTFIELD_FEEDBACK" : TextfieldFeedbackUserAnswer,
        }
        return ANSWER_MODELS[self.question_type]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super(ContentFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        pass

    def get_human_readable_type(self):
        return self.question_type.replace("_", " ").lower()

    def get_answers_by_content(self, instance, content):
        return self.get_answer_model().objects.filter(question=self, content=content, instance=instance)

    def get_user_answers_by_content(self, user, instance, content):
        return self.get_answer_model().objects.filter(question=self, user=user, content=content, instance=instance)
    
    def get_latest_answer(self, user, instance, content):
        answers = self.get_user_answers_by_content(user, instance, content)
        if answers:
            return answers.latest()
        else:
            return None

    def get_latest_answers_by_content(self, instance, content):
        return self.get_answers_by_content(instance, content).order_by("user", "-answer_date").distinct("user")

    def user_answered(self, user, instance, content):
        return self.get_answer_model().objects.filter(question=self, user=user, content=content, instance=instance).count() >= 1
            
    class Meta:
        ordering = ["question_type"]

class TextfieldFeedbackQuestion(ContentFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "TEXTFIELD_FEEDBACK"
        super(TextfieldFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        if "text-feedback" in answer.keys():
            given_answer = answer["text-feedback"].replace("\r", "")
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read text feedback from the feedback field!")
        
        if not given_answer:
            raise InvalidFeedbackAnswerException("Your answer is missing!")

        answer_object = TextfieldFeedbackUserAnswer(
            question=self, content=content, instance=instance, answer=given_answer, user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object
                
    class Meta:
        verbose_name = "content textfield feedback question"
        proxy = True

class ThumbFeedbackQuestion(ContentFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "THUMB_FEEDBACK"
        super(ThumbFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        if "choice" in answer.keys():
            choice = answer["choice"]
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the selected feedback option!")

        if choice == "up":
            thumb_up = True
        else:
            thumb_up = False

        answer_object = ThumbFeedbackUserAnswer(
            question=self, content=content, instance=instance, thumb_up=thumb_up, user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object
        
    class Meta:
        verbose_name = "content thumb feedback question"
        proxy = True

class StarFeedbackQuestion(ContentFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "STAR_FEEDBACK"
        super(StarFeedbackQuestion, self).save(*args, **kwargs)
    
    def save_answer(self, instance, content, user, ip, answer):
        if "choice" in answer.keys():
            rating = int(answer["choice"])
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the selected rating!")

        answer_object = StarFeedbackUserAnswer(
            question=self, instance=instance, content=content, rating=rating, user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object
        
    class Meta:
        verbose_name = "content star feedback question"
        proxy = True

class MultipleChoiceFeedbackQuestion(ContentFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "MULTIPLE_CHOICE_FEEDBACK"
        super(MultipleChoiceFeedbackQuestion, self).save(*args, **kwargs)
    
    def save_answer(self, instance, content, user, ip, answer):
        if "choice" in answer.keys():
            choice = int(answer["choice"])
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the chosen answer!")

        answer_object = MultipleChoiceFeedbackUserAnswer(
            question=self, instance=instance, content=content, chosen_answer=MultipleChoiceFeedbackAnswer.objects.get(id=choice), user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object

    def get_choices(self):
        choices = MultipleChoiceFeedbackAnswer.objects.filter(question=self.id).order_by('id')
        return choices
        
    class Meta:
        verbose_name = "content multiple choice feedback question"
        proxy = True

class MultipleChoiceFeedbackAnswer(models.Model):
    #TODO: is there a need for setting maximum count of answer choices per feedback question?
    
    question = models.ForeignKey(MultipleChoiceFeedbackQuestion, on_delete=models.CASCADE)
    answer = models.TextField(blank=False)

    def __str__(self):
        return self.answer

class ContentFeedbackUserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)                          # The user who has given this feedback
    content = models.ForeignKey('courses.ContentPage', on_delete=models.CASCADE)      # The content on which this feedback was given
    question = models.ForeignKey(ContentFeedbackQuestion, on_delete=models.CASCADE)   # The feedback question this feedback answers
    answerer_ip = models.GenericIPAddressField()
    answer_date = models.DateTimeField(verbose_name='Date and time of when the user answered this feedback question',
                                       auto_now_add=True)
    instance = models.ForeignKey('courses.CourseInstance', null=True, on_delete=models.SET_NULL)
   
class TextfieldFeedbackUserAnswer(ContentFeedbackUserAnswer):
    answer = models.TextField()

    class Meta:
        get_latest_by = "answer_date"
    
class ThumbFeedbackUserAnswer(ContentFeedbackUserAnswer):
    thumb_up = models.BooleanField()
    
    class Meta:
        get_latest_by = "answer_date"

class StarFeedbackUserAnswer(ContentFeedbackUserAnswer):
    rating = models.PositiveSmallIntegerField()
    
    class Meta:
        get_latest_by = "answer_date"

class MultipleChoiceFeedbackUserAnswer(ContentFeedbackUserAnswer):
    chosen_answer = models.ForeignKey(MultipleChoiceFeedbackAnswer, on_delete=models.CASCADE)

    def __str__(self):
        return self.chosen_answer.answer
    
    class Meta:
        get_latest_by = "answer_date"

class InvalidFeedbackAnswerException(Exception):
    """
    This exception is cast when a feedback answer cannot be processed.
    """
    pass

class DatabaseBackendException(Exception):
    """
    This exception is cast when the database backend does not support the attempted operation.
    """
    pass
