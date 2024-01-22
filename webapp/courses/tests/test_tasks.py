import datetime
import json
import os
import shutil

import redis
from django.core import files
from django.conf import settings
from django.test import TestCase
from django.utils import translation
from reversion import revisions as reversion
from reversion.models import Version

import courses.models as cm
from courses.tasks import add, run_tests
import courses.tests.testhelpers as helpers


TEST_CHECKER_CODE = """
import importlib
import json
import sys
if __name__ == "__main__":
    module_name = sys.argv[1]
    name = module_name.rsplit(".py", 1)[0]
    st_module = importlib.import_module(name)

    result_str = st_module.answer()
    if result_str == "correct":
        msg = "testing correct answer"
        flag = 1
    elif result_str == "incorrect":        
        msg = "testing incorrect answer"
        flag = 0
    else:
        msg = "testing error"
        flag = 3

    response = {
        "tester": "test test",
        "tests": [
            {
                "title": "Testing single test with 1 run",
                "runs": [
                    {
                        "output": [
                            {
                                "msg": msg,
                                "flag": flag
                            }
                        ]
                    }
                ]
            }
        ]
    }
    print(json.dumps(response))
"""

TEST_ANSWER_CODE = """
def answer():
    return "{answer}"
"""

TEST_ANSWER_EXC = """
def answer():
    raise RunTimeError
"""

TEST_ANSWER_TIMEOUT = """
import time
def answer():
    time.sleep(10)
"""

TEST_ANSWER_PRINTS = """
def answer():
    print("imma bork you")
"""


class TaskTimeoutError(Exception):
    pass


def create_answerable_exercise():
    with reversion.create_revision():
        exercise = cm.FileUploadExercise(
            name="answerable file upload exercise",
            content="some content",
            default_points=1,
        )
        exercise.save()

        checker = cm.FileExerciseTestIncludeFile()
        checker.exercise = exercise
        file_settings = cm.IncludeFileSettings()

        checker.default_name = "test_checker.py"
        checker.fileinfo = files.base.ContentFile(TEST_CHECKER_CODE, "test_checker.py")

        file_settings.name = "test_checker.py"
        file_settings.purpose = "TEST"

        file_settings.save()

        checker.file_settings = file_settings
        checker.save()

        test = cm.FileExerciseTest()
        test.exercise = exercise
        test.name = "test_test"
        test.save()
        test.required_files.set([checker])
        test.save()

        stage = cm.FileExerciseTestStage()
        stage.test = test
        stage.name = "test test stage"
        stage.ordinal_number = 1
        stage.save()

        command = cm.FileExerciseTestCommand()
        command.stage = stage
        command.command_line = "python3 test_checker.py $RETURNABLES"
        command.json_output = True
        command.ordinal_number = 1
        command.save()

    revision = Version.objects.get_for_object(exercise).latest("revision__date_created").revision_id

    return exercise, revision


def create_answerable_file_upload_exercise_page(exercise):
    page = cm.Lecture(
        name="answerable upload exercise page",
        content=f"<!page={exercise.slug}>",
    )
    page.save()
    return page


def create_answer(answer_code, user, instance, exercise, revision):
    answer = cm.UserFileUploadExerciseAnswer(
        instance=instance,
        exercise=exercise,
        revision=revision,
        user=user,
        answer_date=datetime.datetime.now(),
        answerer_ip="127.0.0.1",
    )
    answer.save()

    returnfile = cm.FileUploadExerciseReturnFile()
    returnfile.fileinfo = files.base.ContentFile(answer_code, "test_answer.py")
    returnfile.answer = answer
    returnfile.save()

    return answer


class TaskTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """
        Aborts testing if the settings file has not been explicitly marked as
        test configuration settings. This is a safeguard against accidentally
        wiping a dev or production media root empty at teardown.
        """

        if getattr(settings, "TEST_SETTINGS", False):
            super().setUpClass()
        else:
            raise helpers.TestSettingsNotUsed(
                "Using a settings file without TEST_SETTINGS set to True is not allowed."
            )

        cls.r = redis.StrictRedis(**settings.REDIS_RESULT_CONFIG)

    @classmethod
    def tearDownClass(cls):
        """
        Remove the media root directory defined in the unit test settings file.
        Needed to clean up files written to disk when creating media models for
        tests.
        """

        super().tearDownClass()
        if getattr(settings, "TEST_SETTINGS", False):
            shutil.rmtree(settings.MEDIA_ROOT)
            os.rmdir(os.path.dirname(settings.MEDIA_ROOT))
        # cls.celery_worker.__exit__()

    @classmethod
    def setUpTestData(cls):
        """
        Sets up an answerable file upload exercise
        """

        user = helpers.create_admin_user()
        test_frontpage = helpers.create_frontpage()
        exercise, revision = helpers.create_answerable_exercise()
        test_page_file_upload = helpers.create_answerable_file_upload_exercise_page(exercise)
        # test_page_template = create_template_exercise_page()
        __, test_instance = helpers.create_course_with_instance()
        helpers.add_content_graph(test_frontpage, test_instance, 0)
        helpers.add_content_graph(test_page_file_upload, test_instance, 6)
        # add_content_graph(test_page_template, test_instance, 7)
        test_instance.frontpage = test_frontpage
        test_instance.save()
        # cls.timeout_answer = create_answer(TEST_ANSWER_TIMEOUT, user, test_instance, exercise, revision)
        # cls.exc_answer = create_answer(TEST_ANSWER_EXC, user, test_instance, exercise, revision)
        cls.instance = test_instance
        cls.exercise = exercise
        cls.user = user
        cls.revision = revision

    def test_add(self):
        task = add.s(1, 1).apply()
        self.assertEqual(task.result, 2)

    def _submit_file_upload_answer(self, answer_id):
        result = run_tests.s(
            user_id=self.user.id,
            instance_id=self.instance.id,
            exercise_id=self.exercise.id,
            answer_id=answer_id,
            lang_code=translation.get_language(),
            revision=None,
        ).apply()
        evaluation_id = result.get()
        result.forget()
        evaluation_obj = cm.Evaluation.objects.get(id=evaluation_id)
        return result, evaluation_obj

    def test_file_upload_answering_correct(self):
        answer = create_answer(
            TEST_ANSWER_CODE.format(answer="correct"),
            self.user,
            self.instance,
            self.exercise,
            self.revision,
        )
        result, evaluation_obj = self._submit_file_upload_answer(answer.id)
        self.assertEqual(evaluation_obj.correct, True)
        result_json = json.loads(self.r.get(result.task_id).decode("utf-8"))
        self.r.delete(result.task_id)
        log = result_json["test_tree"]["log"]
        self.assertEqual(log[0]["runs"][0]["output"][0]["flag"], 1)

    def test_file_upload_answering_incorrect(self):
        answer = create_answer(
            TEST_ANSWER_CODE.format(answer="incorrect"),
            self.user,
            self.instance,
            self.exercise,
            self.revision,
        )
        result, evaluation_obj = self._submit_file_upload_answer(answer.id)
        self.assertEqual(evaluation_obj.correct, False)
        result_json = json.loads(self.r.get(result.task_id).decode("utf-8"))
        self.r.delete(result.task_id)
        log = result_json["test_tree"]["log"]
        self.assertEqual(log[0]["runs"][0]["output"][0]["flag"], 0)

    def test_file_upload_answering_error(self):
        answer = create_answer(
            TEST_ANSWER_CODE.format(answer="error"),
            self.user,
            self.instance,
            self.exercise,
            self.revision,
        )
        result, evaluation_obj = self._submit_file_upload_answer(answer.id)
        self.assertEqual(evaluation_obj.correct, False)
        result_json = json.loads(self.r.get(result.task_id).decode("utf-8"))
        self.r.delete(result.task_id)
        log = result_json["test_tree"]["log"]
        self.assertEqual(log[0]["runs"][0]["output"][0]["flag"], 3)

    def test_file_upload_answer_timeout(self):
        answer = create_answer(
            TEST_ANSWER_TIMEOUT, self.user, self.instance, self.exercise, self.revision
        )
        result, evaluation_obj = self._submit_file_upload_answer(answer.id)
        self.assertEqual(evaluation_obj.correct, False)
        result_json = json.loads(self.r.get(result.task_id).decode("utf-8"))
        self.r.delete(result.task_id)
        self.assertEqual(result_json["test_tree"]["log"], [])
        self.assertEqual(
            result_json["test_tree"]["tests"][0]["stages"][0]["commands"][0]["timedout"],
            True,
        )

    def test_file_upload_answer_broken_checker(self):
        """
        Tests raising an exception inside a checker that doesn't catch
        exceptions caused by the answer code.
        """

        answer = create_answer(
            TEST_ANSWER_EXC, self.user, self.instance, self.exercise, self.revision
        )
        result, evaluation_obj = self._submit_file_upload_answer(answer.id)
        self.assertEqual(evaluation_obj.correct, False)
        result_json = json.loads(self.r.get(result.task_id).decode("utf-8"))
        self.r.delete(result.task_id)
        self.assertEqual(result_json["test_tree"]["log"], [])
        self.assertEqual(len(result_json["test_tree"]["errors"]), 2)

    def test_file_upload_answer_prints(self):
        """
        Tests priting into the std output inside a checker that doesn't catch
        output of the answer code. Currently this breaks the checker because
        its output is no longer parseable JSON.
        """

        answer = create_answer(
            TEST_ANSWER_PRINTS, self.user, self.instance, self.exercise, self.revision
        )
        result, evaluation_obj = self._submit_file_upload_answer(answer.id)
        self.assertEqual(evaluation_obj.correct, False)
        result_json = json.loads(self.r.get(result.task_id).decode("utf-8"))
        self.r.delete(result.task_id)
        self.assertEqual(result_json["test_tree"]["log"], [])
        self.assertEqual(len(result_json["test_tree"]["errors"]), 1)
