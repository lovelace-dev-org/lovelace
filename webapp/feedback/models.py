from django.utils.text import slugify
from django.db import models
from django.contrib.auth.models import User
import django.conf
from utils.management import ExportImportMixin, get_prefixed_slug

# from courses.models import ContentPage # prevent circular import

## Feedback models

QUESTION_TYPE_CHOICES = (
    ("THUMB_FEEDBACK", "Thumb feedback"),
    ("STAR_FEEDBACK", "Star feedback"),
    ("MULTIPLE_CHOICE_FEEDBACK", "Multiple choice feedback"),
    ("TEXTFIELD_FEEDBACK", "Textfield feedback"),
)


class FeedbackManager(models.Manager):

    def get_by_natural_key(self, slug):
        return self.get(slug=slug)


class ContentFeedbackQuestion(models.Model, ExportImportMixin):
    """A feedback that can be linked to any content."""

    class Meta:
        ordering = ["question_type"]

    objects = FeedbackManager()

    question = models.CharField(verbose_name="Question", max_length=100)
    question_type = models.CharField(
        max_length=28, default="TEXTFIELD_FEEDBACK", choices=QUESTION_TYPE_CHOICES
    )
    origin = models.ForeignKey("courses.Course", null=True, on_delete=models.SET_NULL)
    slug = models.SlugField(max_length=255, db_index=True, unique=True, allow_unicode=True)

    def natural_key(self):
        return [self.slug]

    def __str__(self):
        return self.question

    def get_url_name(self):
        """Creates a URL and HTML5 ID field friendly version of the name."""
        return get_prefixed_slug(self, self.origin, "question")

    def get_type_object(self):
        """
        Returns the actual type object of the question object that
        is the child of ContentFeedbackQuestion.
        """

        type_models = {
            "THUMB_FEEDBACK": ThumbFeedbackQuestion,
            "STAR_FEEDBACK": StarFeedbackQuestion,
            "MULTIPLE_CHOICE_FEEDBACK": MultipleChoiceFeedbackQuestion,
            "TEXTFIELD_FEEDBACK": TextfieldFeedbackQuestion,
        }
        return type_models[self.question_type].objects.get(id=self.id)

    def get_answer_model(self):
        """
        Returns the corresponding answer model of the question object
        that is the child of ContentFeedbackQuestion.
        """

        answer_models = {
            "THUMB_FEEDBACK": ThumbFeedbackUserAnswer,
            "STAR_FEEDBACK": StarFeedbackUserAnswer,
            "MULTIPLE_CHOICE_FEEDBACK": MultipleChoiceFeedbackUserAnswer,
            "TEXTFIELD_FEEDBACK": TextfieldFeedbackUserAnswer,
        }
        return answer_models[self.question_type]

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        super().save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        pass

    def get_human_readable_type(self):
        return self.question_type.replace("_", " ").lower()

    def get_answers_by_content(self, instance, content):
        return self.get_answer_model().objects.filter(
            question=self, content=content, instance=instance
        )

    def get_user_answers_by_content(self, user, instance, content):
        return self.get_answer_model().objects.filter(
            question=self, user=user, content=content, instance=instance
        )

    def get_latest_answer(self, user, instance, content):
        answers = self.get_user_answers_by_content(user, instance, content)
        if answers:
            return answers.latest()
        return None

    def get_latest_answers_by_content(self, instance, content):
        return (
            self.get_answers_by_content(instance, content)
            .order_by("user", "-answer_date")
            .distinct("user")
        )

    def user_answered(self, user, instance, content):
        return (
            self.get_answer_model()
            .objects.filter(question=self, user=user, content=content, instance=instance)
            .count()
            >= 1
        )



class TextfieldFeedbackQuestion(ContentFeedbackQuestion):
    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "TEXTFIELD_FEEDBACK"
        super().save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        if "text-feedback" in answer.keys():
            given_answer = answer["text-feedback"].replace("\r", "")
        else:
            raise InvalidFeedbackAnswerException(
                "Error: failed to read text feedback from the feedback field!"
            )

        if not given_answer:
            raise InvalidFeedbackAnswerException("Your answer is missing!")

        answer_object = TextfieldFeedbackUserAnswer(
            question=self,
            content=content,
            instance=instance,
            answer=given_answer,
            user=user,
            answerer_ip=ip,
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
        super().save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        try:
            choice = answer["choice"]
        except KeyError as e:
            raise InvalidFeedbackAnswerException(
                "Error: failed to read the selected feedback option!"
            ) from e

        answer_object = ThumbFeedbackUserAnswer(
            question=self,
            content=content,
            instance=instance,
            thumb_up=choice == "up",
            user=user,
            answerer_ip=ip,
        )
        answer_object.save()
        return answer_object

    class Meta:
        verbose_name = "content thumb feedback question"
        proxy = True


class StarFeedbackQuestion(ContentFeedbackQuestion):
    class Meta:
        verbose_name = "content star feedback question"
        proxy = True

    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "STAR_FEEDBACK"
        super().save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        try:
            rating = int(answer["choice"])
        except KeyError as e:
            raise InvalidFeedbackAnswerException(
                "Error: failed to read the selected rating!"
            ) from e

        answer_object = StarFeedbackUserAnswer(
            question=self,
            instance=instance,
            content=content,
            rating=rating,
            user=user,
            answerer_ip=ip,
        )
        answer_object.save()
        return answer_object


class MultipleChoiceFeedbackQuestion(ContentFeedbackQuestion):

    class Meta:
        verbose_name = "content multiple choice feedback question"
        proxy = True


    def save(self, *args, **kwargs):
        self.slug = self.get_url_name()
        self.question_type = "MULTIPLE_CHOICE_FEEDBACK"
        super().save(*args, **kwargs)

    def save_answer(self, instance, content, user, ip, answer):
        try:
            choice = int(answer["choice"])
        except KeyError as e:
            raise InvalidFeedbackAnswerException("Error: failed to read the chosen answer!") from e

        answer_object = MultipleChoiceFeedbackUserAnswer(
            question=self,
            instance=instance,
            content=content,
            chosen_answer=MultipleChoiceFeedbackAnswer.objects.get(id=choice),
            user=user,
            answerer_ip=ip,
        )
        answer_object.save()
        return answer_object

    def get_choices(self):
        choices = MultipleChoiceFeedbackAnswer.objects.filter(question=self.id).order_by("id")
        return choices

    def export(self, instance, export_target):
        super(ContentFeedbackQuestion, self).export(instance, export_target)
        export_json(
            serialize_many_python(self.get_choices()),
            f"{self.slug}_choices",
            export_target,
        )


class MultipleChoiceFeedbackAnswer(models.Model):
    question = models.ForeignKey(MultipleChoiceFeedbackQuestion, on_delete=models.CASCADE)
    answer = models.TextField(blank=False)

    def natural_key(self):
        return [self.question.slug, self.answer]

    def __str__(self):
        return self.answer


class ContentFeedbackUserAnswer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # The user who has given this feedback
    content = models.ForeignKey(
        "courses.ContentPage", on_delete=models.CASCADE
    )  # The content on which this feedback was given
    question = models.ForeignKey(
        ContentFeedbackQuestion, on_delete=models.CASCADE
    )  # The feedback question this feedback answers
    answerer_ip = models.GenericIPAddressField()
    answer_date = models.DateTimeField(
        verbose_name="Date and time of when the user answered this feedback question",
        auto_now_add=True,
    )
    instance = models.ForeignKey("courses.CourseInstance", null=True, on_delete=models.SET_NULL)


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


class DatabaseBackendException(Exception):
    """
    This exception is cast when the database backend does not support the attempted operation.
    """

def export_models(instance, export_target):
    for question in ContentFeedbackQuestion.objects.all():
        question.export(instance, export_target)

def get_import_list():
    return [
        ContentFeedbackQuestion,
        MultipleChoiceFeedbackAnswer
    ]
