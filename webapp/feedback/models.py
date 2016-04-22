from django.utils.text import slugify
from django.db import models
from django.contrib.auth.models import User
from django.db.models import F
from django.db.models import Max
from django.db import connection

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
    question = models.CharField(verbose_name="Question", max_length=100, unique=True)
    question_type = models.CharField(max_length=28, default="TEXTFIELD_FEEDBACK", choices=QUESTION_TYPE_CHOICES)
    slug = models.SlugField(max_length=255, db_index=True, unique=True)
    
    def __str__(self):
        return self.question

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        return slugify(self.question)
    
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
            self.slug = slugify(self.slug)

        super(ContentFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, content, user, ip, answer):
        pass

    def get_human_readable_type(self):
        return self.question_type.replace("_", " ").lower()

    def get_answers_by_content(self, content):
        return self.get_answer_model().objects.filter(question=self, content=content)

    def get_user_answers_by_content(self, user, content):
        return self.get_answer_model().objects.filter(question=self, user=user, content=content)
    
    def get_latest_answer(self, user, content):
        answers = self.get_user_answers_by_content(user, content)
        if answers:
            return answers.latest()
        else:
            return None

    def get_latest_answers_by_content(self, content):
        return self.get_answers_by_content(content).order_by("user", "-answer_date").distinct("user")

    def user_answered(self, user, content):
        return self.get_answer_model().objects.filter(question=self, user=user, content=content).count() >= 1
            
    class Meta:
        ordering = ["question_type"]

class TextfieldFeedbackQuestion(ContentFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "TEXTFIELD_FEEDBACK"
        super(TextfieldFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, content, user, ip, answer):
        if "text-feedback" in answer.keys():
            given_answer = answer["text-feedback"].replace("\r", "")
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read text feedback from the feedback field!")
        
        if not given_answer:
            raise InvalidFeedbackAnswerException("Your answer is missing!")

        answer_object = TextfieldFeedbackUserAnswer(
            question=self, content=content, answer=given_answer, user=user,
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

    def save_answer(self, content, user, ip, answer):
        if "choice" in answer.keys():
            choice = answer["choice"]
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the selected feedback option!")

        if choice == "up":
            thumb_up = True
        else:
            thumb_up = False

        answer_object = ThumbFeedbackUserAnswer(
            question=self, content=content, thumb_up=thumb_up, user=user,
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
    
    def save_answer(self, content, user, ip, answer):
        if "choice" in answer.keys():
            rating = int(answer["choice"])
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the selected rating!")

        answer_object = StarFeedbackUserAnswer(
            question=self, content=content, rating=rating, user=user,
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
    
    def save_answer(self, content, user, ip, answer):
        if "choice" in answer.keys():
            choice = int(answer["choice"])
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the chosen answer!")

        answer_object = MultipleChoiceFeedbackUserAnswer(
            question=self, content=content, chosen_answer=MultipleChoiceFeedbackAnswer.objects.get(id=choice), user=user,
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
    question = models.ForeignKey(MultipleChoiceFeedbackQuestion)
    answer = models.TextField()

    def __str__(self):
        return self.answer

class ContentFeedbackUserAnswer(models.Model):
    user = models.ForeignKey(User)                          # The user who has given this feedback
    content = models.ForeignKey('courses.ContentPage')      # The content on which this feedback was given
    question = models.ForeignKey(ContentFeedbackQuestion)   # The feedback question this feedback answers
    answerer_ip = models.GenericIPAddressField()
    answer_date = models.DateTimeField(verbose_name='Date and time of when the user answered this feedback question',
                                       auto_now_add=True)
   
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
    chosen_answer = models.ForeignKey(MultipleChoiceFeedbackAnswer)

    def __str__(self):
        return self.chosen_answer
    
    class Meta:
        get_latest_by = "answer_date"

class EmbeddedFeedbackQuestion(models.Model):
    """A feedback that can be embedded to a content page."""
    question = models.CharField(verbose_name="Question", max_length=100, unique=True)
    question_type = models.CharField(max_length=28, default="TEXTFIELD_FEEDBACK", choices=QUESTION_TYPE_CHOICES)
    description = models.TextField(blank=True, null=True)
    slug = models.CharField(max_length=255, db_index=True, unique=True)
    
    def __str__(self):
        return self.question

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        return slugify.slugify(self.question)
    
    def get_type_object(self):
        """Returns the actual type object of the question object that is the child of EmbeddedFeedbackQuestion."""
        TYPE_MODELS = {
            "THUMB_FEEDBACK" : EmbeddedThumbFeedbackQuestion,
            "STAR_FEEDBACK" : EmbeddedStarFeedbackQuestion,
            "MULTIPLE_CHOICE_FEEDBACK": EmbeddedMultipleChoiceFeedbackQuestion,
            "TEXTFIELD_FEEDBACK" : EmbeddedTextfieldFeedbackQuestion,
        }
        return TYPE_MODELS[self.question_type].objects.get(id=self.id)

    def get_answer_model(self):
        """Returns the corresponding answer model of the question object that is the child of EmbeddedFeedbackQuestion."""
        ANSWER_MODELS = {
            "THUMB_FEEDBACK" : EmbeddedThumbFeedbackUserAnswer,
            "STAR_FEEDBACK" : EmbeddedStarFeedbackUserAnswer,
            "MULTIPLE_CHOICE_FEEDBACK": EmbeddedMultipleChoiceFeedbackUserAnswer,
            "TEXTFIELD_FEEDBACK" : EmbeddedTextfieldFeedbackUserAnswer,
        }
        return ANSWER_MODELS[self.question_type]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify.slugify(self.slug)

        super(EmbeddedFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, course_inst, user, ip, answer):
        pass

    def get_human_readable_type(self):
        return self.question_type.replace("_", " ").lower()

    def get_answers_by_course_inst(self, course_inst):
        return self.get_answer_model().objects.filter(question=self, course_instance=course_inst)

    def get_user_answers_by_course_inst(self, user, course_inst):
        return self.get_answer_model().objects.filter(question=self, user=user, course_instance=course_inst)
    
    def get_latest_answer(self, user, course_inst):
        answers = self.get_user_answers_by_course_inst(user, course_inst)
        if answers:
            return answers.latest()
        else:
            return None

    def get_latest_answers_by_course_inst(self, course_inst):
        if connection.vendor == "postgresql":
            return self.get_answers_by_course_inst(course_inst).order_by("user", "-answer_date").distinct("user")
        else:
            raise DatabaseBackendException("Database backend does not support DISTINCT ON")

    def user_answered(self, user, course_inst):
        return self.get_answer_model().objects.filter(question=self, user=user, course_instance=course_inst).count() >= 1
            
    class Meta:
        ordering = ["question_type"]

class EmbeddedTextfieldFeedbackQuestion(EmbeddedFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "TEXTFIELD_FEEDBACK"
        super(EmbeddedTextfieldFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, course_inst, user, ip, answer):
        if "text-feedback" in answer.keys():
            given_answer = answer["text-feedback"].replace("\r", "")
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read text feedback from the feedback field!")
        
        if not given_answer:
            raise InvalidFeedbackAnswerException("Your answer is missing!")

        answer_object = EmbeddedTextfieldFeedbackUserAnswer(
            question=self, course_instance=course_inst, answer=given_answer, user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object
                
    class Meta:
        verbose_name = "embedded textfield feedback question"
        proxy = True

class EmbeddedThumbFeedbackQuestion(EmbeddedFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "THUMB_FEEDBACK"
        super(EmbeddedThumbFeedbackQuestion, self).save(*args, **kwargs)

    def save_answer(self, course_inst, user, ip, answer):
        if "choice" in answer.keys():
            choice = answer["choice"]
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the selected feedback option!")

        if choice == "up":
            thumb_up = True
        else:
            thumb_up = False

        answer_object = EmbeddedThumbFeedbackUserAnswer(
            question=self, course_instance=course_inst, thumb_up=thumb_up, user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object
        
    class Meta:
        verbose_name = "embedded thumb feedback question"
        proxy = True

class EmbeddedStarFeedbackQuestion(EmbeddedFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "STAR_FEEDBACK"
        super(EmbeddedStarFeedbackQuestion, self).save(*args, **kwargs)
    
    def save_answer(self, course_inst, user, ip, answer):
        if "choice" in answer.keys():
            rating = int(answer["choice"])
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the selected rating!")

        answer_object = EmbeddedStarFeedbackUserAnswer(
            question=self, course_instance=course_inst, rating=rating, user=user,
            answerer_ip=ip
        )
        answer_object.save()
        return answer_object
        
    class Meta:
        verbose_name = "embedded star feedback question"
        proxy = True

class EmbeddedMultipleChoiceFeedbackQuestion(EmbeddedFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "MULTIPLE_CHOICE_FEEDBACK"
        super(EmbeddedMultipleChoiceFeedbackQuestion, self).save(*args, **kwargs)
    
    def save_answer(self, content, user, ip, answer):
        if "choice" in answer.keys():
            choice = int(answer["choice"])
        else:
            raise InvalidFeedbackAnswerException("Error: failed to read the chosen answer!")

        answer_object = EmbeddedMultipleChoiceFeedbackUserAnswer(
            question=self, course_inst=course_inst, chosen_answer=EmbeddedMultipleChoiceFeedbackAnswer.objects.get(id=choice), 
            user=user, answerer_ip=ip
        )
        answer_object.save()
        return answer_object

    def get_choices(self):
        choices = EmbeddedMultipleChoiceFeedbackAnswer.objects.filter(question=self.id).order_by('id')
        return choices
        
    class Meta:
        verbose_name = "embedded multiple choice feedback question"
        proxy = True

class EmbeddedMultipleChoiceFeedbackAnswer(models.Model):
    question = models.ForeignKey(EmbeddedMultipleChoiceFeedbackQuestion)
    answer = models.TextField()

    def __str__(self):
        return self.answer

class EmbeddedFeedbackUserAnswer(models.Model):
    user = models.ForeignKey(User)                                  # The user who has given this feedback
    course_instance = models.ForeignKey('courses.CourseInstance')   # The course instance on which this feedback was given
    question = models.ForeignKey(EmbeddedFeedbackQuestion)          # The feedback question this feedback answers
    answerer_ip = models.GenericIPAddressField()
    answer_date = models.DateTimeField(verbose_name='Date and time of when the user answered this feedback question',
                                       auto_now_add=True)

class EmbeddedTextfieldFeedbackUserAnswer(EmbeddedFeedbackUserAnswer):
    answer = models.TextField()

    class Meta:
        get_latest_by = "answer_date"
    
class EmbeddedThumbFeedbackUserAnswer(EmbeddedFeedbackUserAnswer):
    thumb_up = models.BooleanField()
    
    class Meta:
        get_latest_by = "answer_date"

class EmbeddedStarFeedbackUserAnswer(EmbeddedFeedbackUserAnswer):
    rating = models.PositiveSmallIntegerField()
    
    class Meta:
        get_latest_by = "answer_date"

class EmbeddedMultipleChoiceFeedbackUserAnswer(EmbeddedFeedbackUserAnswer):
    chosen_answer = models.ForeignKey(EmbeddedMultipleChoiceFeedbackAnswer)

    def __str__(self):
        return self.chosen_answer
    
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
