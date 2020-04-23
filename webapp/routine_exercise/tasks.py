from __future__ import absolute_import

import csv
import io
import json
import os
import random
import redis
import resource
import shlex
import string
import subprocess
import tempfile
import time

from celery import shared_task
from django.conf import settings
from django.core.cache import cache
from django.urls import reverse
from django.utils import translation

from courses import evaluation_sec as sec
from courses.models import Course, CourseInstance, UserFileUploadExerciseAnswer
from routine_exercise.models import *
from utils.content import get_instance_revision
from utils.files import get_file_contents

def _run_command(args, test_dir):
    
    # preparations to run the backend
    stdout = tempfile.TemporaryFile(dir=settings.TMP_PATH)
    stderr = tempfile.TemporaryFile(dir=settings.TMP_PATH)

    demote_process = sec.default_demote_process
    start_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start_time = time.time()

    env = {
        'PWD': test_dir,
        'PATH': settings.CHECKER_PYTHON_PATH,
        'LC_CTYPE': 'en_US.UTF-8',
    }

    proc_results = {
        "command_line": " ".join(shlex.quote(arg) for arg in args)
    }

    # run the command in initialization mode
    try:
        proc = subprocess.Popen(
            args=args,
            bufsize=-1,
            executable=None,
            stdout=stdout,
            stderr=stderr,
            preexec_fn=demote_process,
            close_fds=True,
            shell=False,
            cwd=test_dir,
            env=env,
            universal_newlines=False
        )
    except (FileNotFoundError, PermissionError) as e:
        proc_results.update({
            "retval": None,
            "timedout": False,
            "killed": False,
            "runtime": 0,
            "error": str(e),
            "fail": True
        })
        return proc_results

    proc_retval = None
    proc_timedout = False
    proc_killed = False

    try:
        proc.wait(timeout=10)
        proc_runtime = time.time() - start_time
        proc_retval = proc.returncode
    except subprocess.TimeoutExpired:
        proc_runtime = time.time() - start_time
        proc_retval = None
        proc_timedout = True
        proc.terminate() # Try terminating the process nicely
        time.sleep(0.5)  # Grace period to allow the process to terminate

    end_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
    ru_utime = end_rusage.ru_utime - start_rusage.ru_utime
    ru_stime = end_rusage.ru_stime - start_rusage.ru_stime

    proc_results.update({
        'retval': proc_retval,
        'timedout': proc_timedout,
        'killed': proc_killed,
        'runtime': proc_runtime,
        'usermodetime': ru_utime,
        'kernelmodetime': ru_stime,
    })

    stdout.seek(0)
    output = stdout.read()
    try:
        proc_results["data"] = json.loads(output.decode("utf-8"))
    except json.JSONDecodeError as e:
        stderr.seek(0)
        proc_results["fail"] = True
        proc_results["error"] = stderr.read().decode("utf-8")
    else:
        stderr.seek(0)
        print(stderr.read())

    return proc_results

def _answer_history(user_id, instance_id, exercise_id):
    answers = RoutineExerciseAnswer.objects.filter(
        question__user_id=user_id,
        question__instance_id=instance_id,
        question__exercise_id=exercise_id
    ).order_by("date_answered")
    return [(answer.question.question_class, answer.correct) for answer in answers]

@shared_task(name="routine_exercise.generate_question", bind=True)
def generate_question(self, user_id, instance_id, exercise_id, lang_code, revision, completed):
    translation.activate(lang_code)
    exercise = get_instance_revision(RoutineExercise, exercise_id, revision)

    with tempfile.TemporaryDirectory(dir=settings.TMP_PATH) as test_dir:

        # prepare backend files
        for backend in RoutineExerciseBackendFile.objects.filter(exercise=exercise):
            backend = get_instance_revision(RoutineExerciseBackendFile, backend.id, revision)
            contents = get_file_contents(backend)
            with open(os.path.join(test_dir, backend.filename), "wb") as f:
                f.write(contents)
            print("Wrote {} from {}".format(backend.filename, backend.fileinfo))

        fn = "".join(random.choice(string.ascii_lowercase) for i in range(24)) + ".json"
        data = {
            "history": _answer_history(user_id, instance_id, exercise_id),
            "completed": completed
        }
        with open(os.path.join(test_dir, fn), "w") as f:
            json.dump(data, f)
        args = shlex.split(exercise.routineexercisebackendcommand.command)
        args.append(fn)
        proc_results = _run_command(args, test_dir)

    if proc_results.get("fail") or proc_results.get("killed") or proc_results.get("timedout"):
        return {
            "task": "generate",
            "status": "fail",
            "error": proc_results["error"],
            "instance_id": instance_id,
            "exercise_id": exercise_id,
            "user_id": user_id
        }

    return {
        "task": "generate",
        "status": "success",
        "data": proc_results["data"],
        "exercise_id": exercise_id,
        "instance_id": instance_id,
        "user_id": user_id,
        "lang_code": lang_code,
        "revision": revision
    }

@shared_task(name="routine_exercise.check_answer", bind=True)
def check_answer(self, user_id, instance_id, exercise_id, question_id, answer_id, lang_code, revision):
    translation.activate(lang_code)
    exercise = get_instance_revision(RoutineExercise, exercise_id, revision)
    answer = RoutineExerciseAnswer.objects.get(id=answer_id)
    progress = RoutineExerciseProgress.objects.get(exercise=exercise, user__id=user_id, instance__id=instance_id)

    with tempfile.TemporaryDirectory(dir=settings.TMP_PATH) as test_dir:

        # prepare backend files
        for backend in RoutineExerciseBackendFile.objects.filter(exercise=exercise):
            backend = get_instance_revision(RoutineExerciseBackendFile, backend.id, revision)
            contents = get_file_contents(backend)
            with open(os.path.join(test_dir, backend.filename), "wb") as f:
                f.write(contents)

        args = shlex.split(exercise.routineexercisebackendcommand.command)
        fn = "".join(random.choice(string.ascii_lowercase) for i in range(24)) + ".json"
        data = {
            "answer": answer.given_answer,
            "history": _answer_history(user_id, instance_id, exercise_id),
            "question_class": answer.question.question_class,
            "params": answer.question.generated_json,
            "progress": progress.progress,
            "completed": progress.completed
        }
        with open(os.path.join(test_dir, fn), "w") as f:
            json.dump(data, f)
        args.append("--check")
        args.append(fn)
        proc_results = _run_command(args, test_dir)

    if proc_results.get("fail") or proc_results.get("killed") or proc_results.get("timedout"):
        return {"task": "generate", "status": "fail", "error": proc_results["error"]}

    return {
        "task": "check",
        "status": "success",
        "data": proc_results["data"],
        "exercise_id": exercise_id,
        "instance_id": instance_id,
        "answer_id": answer_id,
        "user_id": user_id,
        "lang_code": lang_code,
        "revision": revision
    }

    