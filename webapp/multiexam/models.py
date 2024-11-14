import datetime
import json
import yaml
from django.core import serializers
from django.db import models
from django.db.models import Q, JSONField
from django.template import loader
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext as _

from courses.models import (
    ContentPage, CourseInstance, Evaluation, User, UserAnswer,
    InvalidExerciseAnswerException
)

from utils.archive import get_single_archived, find_latest_version
from utils.data import (
    export_json, export_files, serialize_single_python, serialize_many_python
)
from utils.files import get_testfile_path, upload_storage
from utils.management import ExportImportMixin


def querydict_to_answer(attempt, querydict, include_certainty=False):
    """
    Turns the querydict object returned from the HTML form to an answer dictionary. The resulting
    dictionary has category keys as its keys. Values are either strings that contain the answer
    to each question (for checking), or tuples that contain the answer and its certainty (for
    storing).

    If the form has category keys that were not part of the exam, their values are discarded.
    """

    valid_keys = attempt.included_categories()
    answer_record = {}

    for key, choices in querydict.lists():
        if key in valid_keys:
            given_answer = "".join(choices)
            if include_certainty:
                answer_record[key] = (given_answer, querydict.get(f"{key}-certainty"))
            else:
                answer_record[key] = given_answer

    return answer_record


class MultipleQuestionExam(ContentPage):
    """
    MultiExam content type model. Defines all of the behavior required for content types to be
    compatible with the rest of the main code.
    """

    template = "multiexam/multiple-question-exam.html"

    class Meta:
        verbose_name = "multiple question exam"
        proxy = True

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "MULTIPLE_QUESTION_EXAM"
        super().save(*args, **kwargs)

    def get_rendered_content(self, context):
        """
        Includes the multiexam content extra template into the rendered markup. This adds
        the 'Start exam' button and related information to the task.
        """

        content = ContentPage._get_rendered_content(self, context)
        t = loader.get_template("multiexam/multiexam-content-extra.html")
        return content + [("extra", t.render(context), -1, 0)]

    def get_question(self, context):
        """
        Gets the question part of the task, no changes to the default.
        """

        return ContentPage._get_question(self, context)

    def get_admin_change_url(self):
        """
        Returns admin change url for the model instance.
        """

        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:multiexam_{adminized_type}_change", args=(self.id,))

    def get_staff_extra(self, context):
        """
        Adds a link to attempt management page to the task's staff tools.
        """

        return [(
            _("Manage attempts"),
            reverse("multiexam:manage_attempts", kwargs={
                "course": context["course"],
                "instance": context["instance"],
                "content": self,
            })
        )]

    def get_choices(self, revision=None):
        """
        This task type has a separate implementation for handling this behavior, so just returns
        None.
        """

        return

    def save_answer(self, user, ip, answer, files, instance, revision):
        """
        Saves student's answer if it was made to a valid and presently open attempt. The student
        answer is saved with certainty information so that certainty can be retained between
        sessions.
        """

        try:
            attempt = MultipleQuestionExamAttempt.objects.get(id=answer.get("attempt_id"))
        except (KeyError, MultipleQuestionExamAttempt.DoesNotExist):
            raise InvalidExerciseAnswerException(_("Matching exam attempt was not found"))

        now = datetime.datetime.now()
        if not (attempt.open_from <= now <= attempt.open_to):
            raise InvalidExerciseAnswerException(_("This exam is closed"))

        revision = attempt.revision or find_latest_version(self).revision_id

        answer_record = querydict_to_answer(attempt, answer, include_certainty=True)
        answer_object = UserMultipleQuestionExamAnswer(
            user=user,
            exercise=self,
            instance=instance,
            attempt=attempt,
            revision=revision,
            answerer_ip=ip,
            answers=answer_record,
        )
        answer_object.save()
        return answer_object

    def check_answer(self, user, ip, answer, files, answer_object, revision):
        """
        Checks a student's answer against the exam attempt's script.
        """

        try:
            attempt = MultipleQuestionExamAttempt.objects.get(id=answer.get("attempt_id"))
        except (KeyError, MultipleQuestionExamAttempt.DoesNotExist):
            raise InvalidExerciseAnswerException("Matching exam attempt was not found")

        answer_record = querydict_to_answer(attempt, answer, include_certainty=False)
        script = attempt.load_exam_script(exclude_correct=False)
        total_score = 0
        max_score = 0
        results = {}
        for key, question in script:
            max_score += question.get("value", 1)
            if set(answer_record.get(key, "")) == set(question["correct"]):
                total_score += question.get("value", 1)
                results[key] = True
            else:
                results[key] = False

        return {
            "evaluation": True,
            "points": total_score,
            "max": max_score,
            "test_results": json.dumps(results),
        }

    def get_user_answers(self, user, instance, ignore_drafts=True):
        if instance is None:
            return UserMultipleQuestionExamAnswer.objects.filter(
                user=user,
                attempt__exam=self,
            )
        else:
            return UserMultipleQuestionExamAnswer.objects.filter(
                attempt__instance=instance,
                user=user,
                attempt__exam=self,
            )

    def export(self, instance, export_target):
        """
        Exports a multiexam instance. Each of model instance, question pool instance, and
        the exam question pool file are exported into separate files.
        """

        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_single_python(self.examquestionpool),
            f"{self.slug}_question_pool",
            export_target,
        )
        export_files(self.examquestionpool, export_target, "backend", translate=True)


class QuestionPoolManager(models.Manager):

    def get_by_natural_key(self, exercise_slug):
        return self.get(exercise__slug=exercise_slug)


class ExamQuestionPool(models.Model):
    """
    The exam question pool submodel for multiexams.
    """
    objects = QuestionPoolManager()

    exercise = models.OneToOneField(MultipleQuestionExam, on_delete=models.CASCADE)
    fileinfo = models.FileField(max_length=255, upload_to=get_testfile_path, storage=upload_storage)

    def natural_key(self):
        return [self.exercise.slug]

    def question_count(self):
        """
        Gets the question count of the exam for displaying it on a page.
        """

        return len(self.load_contents().keys())

    def load_contents(self):
        """
        Load the contents of the question pool file.
        """

        with self.fileinfo.open() as f:
            pool = yaml.safe_load(f)
        return pool

class MultipleQuestionExamAttempt(models.Model):
    """
    One attempt of a multiexam. Indicates a period of time when the exam can be answered, and
    determines which specific questions have been chosen for the exam. Can be created for a single
    user, or all participants.
    """

    exam = models.ForeignKey(MultipleQuestionExam, on_delete=models.CASCADE)
    instance = models.ForeignKey(CourseInstance, on_delete=models.CASCADE)
    revision = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, null=True, on_delete=models.CASCADE)
    questions = models.JSONField()
    open_from = models.DateTimeField(
        verbose_name="Answerable from",
    )
    open_to = models.DateTimeField(
        verbose_name="Answerable until",
    )

    def load_exam_script(self, exclude_correct=True):
        """
        Loads the exam script of this attempt. This opens the exam question file, and forms the
        exam script based on questions that have been selected for the attempt. When getting
        the script for rendering on the frontend, exclude_correct must always be False, otherwise
        correct answers could be accessed via javascript console.
        """

        if self.revision is not None:
            basefile = get_single_archived(self.exam.examquestionpool, self.revision).fileinfo
        else:
            basefile = self.exam.examquestionpool.fileinfo

        with basefile.open() as f:
            pool = yaml.safe_load(f)

        script = []
        for handle, alt_idx in self.questions.items():
            chosen = pool[handle]["alternatives"][int(alt_idx)].copy()
            chosen["value"] = pool[handle].get("value", 1)
            if exclude_correct:
                chosen.pop("correct")
            script.append((handle, chosen))

        return script

    def answer_count(self):
        """
        Counts the number of answers submitted for this exam attempt.
        """

        return UserMultipleQuestionExamAnswer.objects.filter(
            attempt=self,
        ).count()

    def question_count(self):
        """
        Returns the number of questions asked in this attempt.
        """
        return len(self.questions.keys())

    def included_categories(self):
        """
        Returns a list of categories chosen for this exam attempt.
        """
        return self.questions.keys()




class UserMultipleQuestionExamAnswer(UserAnswer):
    """
    Answer model for multiexams.
    """

    exercise = models.ForeignKey(MultipleQuestionExam, on_delete=models.CASCADE)
    attempt = models.ForeignKey(MultipleQuestionExamAttempt, on_delete=models.CASCADE)
    answers = models.JSONField()

    def get_html_repr(self, context):
        script = self.attempt.load_exam_script()
        evaluation = json.loads(self.evaluation.test_results or "{}")
        summary = {}
        for handle, question in script:
            chosen = []
            for choice in self.answers.get(handle, ("", ""))[0]:
                chosen.append(question["options"][choice])
            summary[handle] = (question["summary"], chosen, evaluation.get(handle, False))
        t = loader.get_template("multiexam/answered-exam.html")
        c = {
            "answer_summary": summary.values(),
            "evaluated": bool(evaluation),
        }
        return t.render(c)


ContentPage.register_content_type(
    "MULTIPLE_QUESTION_EXAM", MultipleQuestionExam, UserMultipleQuestionExamAnswer
)

def export_models(instance, export_target):
    """
    All exports are done by MultiExam's export method so this function should do nothing.
    """

    pass

def get_import_list():
    """
    Returns a list model classes that are to be imported, and indicates the order in which they need
    to be imported in.
    """

    return [
        MultipleQuestionExam,
        ExamQuestionPool,
    ]
