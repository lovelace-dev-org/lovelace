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


# Create your models here.

def querydict_to_answer(attempt, querydict, include_certainty=False):
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

    template = "multiexam/multiple-question-exam.html"

    class Meta:
        verbose_name = "multiple question exam"
        proxy = True

    @classmethod
    def new_from_import(cls, document, instance, pk_map):
        new = cls(**document["fields"])
        document["question_pool"]["fields"]["exercise"] = new
        pool = ExamQuestionPool(**document["question_pool"]["fields"])

        print(f"Would add {cls.__name__} {new.name}")
        return new

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self.get_url_name()
        else:
            self.slug = slugify(self.slug, allow_unicode=True)

        self.content_type = "MULTIPLE_QUESTION_EXAM"
        super().save(*args, **kwargs)

    def get_rendered_content(self, context):
        content = ContentPage._get_rendered_content(self, context)
        t = loader.get_template("multiexam/multiexam-content-extra.html")
        return content + [("extra", t.render(context), -1, 0)]

    def get_question(self, context):
        return ContentPage._get_question(self, context)

    def get_admin_change_url(self):
        adminized_type = self.content_type.replace("_", "").lower()
        return reverse(f"admin:multiexam_{adminized_type}_change", args=(self.id,))

    def get_staff_extra(self, context):
        return [(
            _("Manage attempts"),
            reverse("multiexam:manage_attempts", kwargs={
                "course": context["course"],
                "instance": context["instance"],
                "content": self,
            })
        )]

    def get_choices(self, revision=None):
        return

    def save_answer(self, user, ip, answer, files, instance, revision):
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
        super(ContentPage, self).export(instance, export_target)
        export_json(
            serialize_single_python(self.examquestionpool),
            f"{self.slug}_question_pool",
            export_target,
        )
        export_files(self.examquestionpool, export_target, "backend", translate=True)


class ExamQuestionPool(models.Model):

    exercise = models.OneToOneField(MultipleQuestionExam, on_delete=models.CASCADE)
    fileinfo = models.FileField(max_length=255, upload_to=get_testfile_path, storage=upload_storage)

    def question_count(self):
        with self.fileinfo.open() as f:
            n = len(yaml.safe_load(f).keys())
        return n


class MultipleQuestionExamAttempt(models.Model):

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
        if self.revision is not None:
            basefile = get_single_archived(self.exam.examquestionpool, self.revision).fileinfo
        else:
            basefile = self.exam.examquestionpool.fileinfo

        with basefile.open() as f:
            pool = yaml.safe_load(f)

        script = []
        for handle, alt_idx in self.questions.items():
            chosen = pool[handle]["alternatives"][int(alt_idx)].copy()
            if exclude_correct:
                chosen.pop("correct")
            script.append((handle, chosen))

        return script

    def answer_count(self):
        return UserMultipleQuestionExamAnswer.objects.filter(
            attempt=self,
        ).count()

    def question_count(self):
        return len(self.questions.keys())

    def included_categories(self):
        return self.questions.keys()




class UserMultipleQuestionExamAnswer(UserAnswer):

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
    pass

def get_import_list():
    return [
        MultipleQuestionExam,
        ExamQuestionPool,
    ]
