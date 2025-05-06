"""
Celery tasks for checking a user's answers to file upload, code input and code
replace exercises.
"""
from __future__ import absolute_import

import base64
import json
import logging
import os
import random
import resource
import shlex
import subprocess
import tempfile
import time
from itertools import chain as iterchain

from django.db import IntegrityError, transaction
from django.utils import translation
from django.utils.translation import gettext as _
from django.conf import settings as django_settings
from django.contrib.auth.models import User

import redis

from celery import shared_task, group
from celery.signals import worker_process_init

from prettydiff import difflib
from courses import models as cm
from courses import evaluation_sec as sec
from courses.evaluation_utils import *
from utils.files import chmod_parse


JSON_INCORRECT = 0
JSON_CORRECT = 1
JSON_INFO = 2
JSON_ERROR = 3
JSON_DEBUG = 4

logger = logging.getLogger(__name__)

@worker_process_init.connect
def demote_server(**kwargs):
    """
    Drops each worker process to less privileged user defined in the server
    configuration while retaining the ability to lower child processes to even
    more restricted user (as defined in the configuration).
    """

    server_uid, server_gid = sec.get_uid_gid(django_settings.WORKER_USERNAME)
    student_uid, student_gid = sec.get_uid_gid(django_settings.RESTRICTED_USERNAME)
    os.setresgid(server_gid, server_gid, student_gid)
    os.setresuid(server_uid, server_uid, student_uid)
    logger.debug(f"Worker demoted to: {os.getuid()}")


@shared_task(name="add")
def add(a, b):
    """
    A simple task for testing that celery interaction works.
    """

    return a + b


@shared_task(name="courses.run-fileexercise-tests", bind=True)
def run_tests(self, payload):
    logger.debug(f"Starting task as: {os.getuid()}")
    self.update_state(state="PROGRESS", meta={"current": 4, "total": 10})

    tests = payload["tests"]
    resources = payload["resources"]

    student_results = {}
    reference_results = {}

    # Run all the tests for both the returned and reference code
    for i, test in enumerate(tests):
        self.update_state(state="PROGRESS", meta={"current": i, "total": len(tests)})

        results, all_json = run_test(test, resources, student=True)
        student_results.update(results)

        if not all_json:
            results, all_json = run_test(test, resources)

        # if reference is not needed just put the student results there
        reference_results.update(results)

    results = {"student": student_results, "reference": reference_results}
    evaluation = generate_results(results)

    # Save the rendered results into Redis
    task_id = self.request.id
    # r = redis.StrictRedis(**django_settings.REDIS_RESULT_CONFIG)
    # r.set(task_id, json.dumps(evaluation), ex=django_settings.REDIS_RESULT_EXPIRE)
    return {
        "task": "check",
        "status": "success",
        "data": evaluation
    }


def generate_results(results):
    evaluation = {}
    correct = True
    timedout = False
    points = 0
    max_points = 1

    student = results["student"]
    reference = results["reference"]

    # It's possible some of the tests weren't run at all
    unmatched = set(student.keys()) ^ set(reference.keys())
    if unmatched:
        matched = set(student.keys()) & set(reference.keys())
    else:
        matched = reference.keys()

    test_tree = {
        "tests": [],
        "messages": [],
        "errors": [],
        "hints": set(),
        "triggers": set(),
        "log": [],
    }

    #### GO THROUGH ALL TESTS
    # NOTE bad design here, an exercise can essentially only have one json output test.
    #      this is fine by itself, the code just gives a false impression right now.
    for test_id, student_t, reference_t in ((k, student[k], reference[k]) for k in matched):
        current_test = {
            "test_id": test_id,
            "name": student_t["name"],
            "correct": True,
            "stages": [],
        }

        test_tree["tests"].append(current_test)

        student_stages = student_t["stages"]
        reference_stages = reference_t["stages"]

        matched_stages = set(student_stages.keys()) & set(reference_stages.keys())

        #### GO THROUGH ALL STAGES
        for stage_id, student_s, reference_s in (
            (k, student_stages[k], reference_stages[k])
            for k in sorted(matched_stages, key=lambda x: student_stages[x]["ordinal_number"])
        ):
            current_stage = {
                "stage_id": stage_id,
                "name": student_s["name"],
                "ordinal_number": student_s["ordinal_number"],
                "fail": student_s["fail"],
                "commands": [],
            }
            current_test["stages"].append(current_stage)

            student_cmds = student_s["commands"]
            reference_cmds = reference_s["commands"]

            #### GO THROUGH ALL COMMANDS
            for cmd_id, student_c, reference_c in (
                (k, student_cmds[k], reference_cmds[k])
                for k in sorted(
                    student_cmds.keys(), key=lambda x: student_cmds[x]["ordinal_number"]
                )
            ):
                cmd_correct = True
                if student_c.get("fail"):
                    cmd_correct = False
                if student_c.get("timedout"):
                    cmd_correct = False
                    timedout = True

                current_cmd = {
                    "cmd_id": cmd_id,
                }
                current_cmd.update(student_c)
                current_stage["commands"].append(current_cmd)

                # Handle stdin

                current_cmd["input_text"] = current_cmd["input_text"]

                # Handle JSON outputting testers

                if student_c.get("json_output"):
                    student_stdout = student_c["stdout"]
                    try:
                        json_results = json.loads(student_stdout)
                    except json.decoder.JSONDecodeError as e:
                        test_tree["errors"].append(f"JSONDecodeError: {e}")
                        correct = False
                        json_results = {}
                    else:
                        test_tree["log"] = json_results.get("tests", [])
                        for test in json_results.get("tests", []):
                            test_title = test.get("title")
                            test_msg = {"title": test_title, "msgs": []}
                            for test_run in test.get("runs", []):
                                run_correct = True
                                for test_output in test_run.get("output", []):
                                    output_triggers = test_output.get("triggers", [])
                                    output_hints = test_output.get("hints", [])
                                    output_msg = test_output.get("msg", "")
                                    output_flag = test_output.get("flag", 0)

                                    test_tree["triggers"].update(output_triggers)
                                    test_tree["hints"].update(output_hints)
                                    test_msg["msgs"].append(output_msg)

                                    if output_flag == JSON_INCORRECT:
                                        cmd_correct = False
                                        run_correct = False
                                    if output_flag == JSON_ERROR:
                                        cmd_correct = False
                                        run_correct = False
                                test_run["correct"] = run_correct
                            test_tree["messages"].append(test_msg)

                    if student_c["stderr"]:
                        test_tree["errors"].append(student_c["stderr"])
                        correct = False

                    # override old style result determination with new style
                    if "result" in json_results:
                        cmd_correct = json_results["result"]["correct"]
                        points = json_results["result"]["score"]
                        max_points = json_results["result"]["max"]

                else:
                    # Handle stdout

                    student_stdout = student_c["stdout"]
                    reference_stdout = reference_c["stdout"]

                    if student_c["significant_stdout"] and student_stdout != reference_stdout:
                        cmd_correct = False

                    if student_stdout or reference_stdout:
                        stdout_diff = difflib.HtmlDiff().make_table(
                            fromlines=student_stdout.splitlines(),
                            tolines=reference_stdout.splitlines(),
                            fromdesc="Your program's output",
                            todesc="Expected output",
                        )
                    else:
                        stdout_diff = ""
                    current_cmd["stdout_diff"] = stdout_diff

                    # Handle stderr

                    student_stderr = student_c["stderr"]
                    reference_stderr = reference_c["stderr"]

                    if student_c["significant_stderr"] and student_stderr != reference_stderr:
                        cmd_correct = False

                    if student_stderr or reference_stderr:
                        stderr_diff = difflib.HtmlDiff().make_table(
                            fromlines=student_stderr.splitlines(),
                            tolines=reference_stderr.splitlines(),
                            fromdesc="Your program's errors",
                            todesc="Expected errors",
                        )
                    else:
                        stderr_diff = ""
                    current_cmd["stderr_diff"] = stderr_diff

                current_test["correct"] = cmd_correct if current_test["correct"] else False
                if not cmd_correct:
                    correct = False

    # return unique hints and triggers only
    test_tree["hints"] = list(test_tree["hints"])
    test_tree["triggers"] = list(test_tree["triggers"])

    if correct and points == 0:
        points = max_points

    evaluation.update(
        {
            "correct": correct,
            "timedout": timedout,
            "test_tree": test_tree,
            "points": points,
            "max": max_points,
        }
    )

    return evaluation


@shared_task(name="courses.run-test", bind=True)
def run_test(self, test, resources, student=False):
    """
    Runs all the stages of the given test.
    """

    required_files = test["required_files"]

    # Note: requires a shared/cloned file system!
    if student:
        files_to_check = resources["files_to_check"]
    else:
        files_to_check = {}
        for req_file_handle in required_files:
            file_info = resources["checker_files"][req_file_handle]
            if file_info["purpose"] == "REFERENCE":
                files_to_check[file_info["name"]] = file_info["content"]

    temp_dir_prefix = os.path.join("/", "tmp")

    test_results = {test["test_id"]: {"fail": True, "name": test["name"], "stages": {}}}
    with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as test_dir:
        os.chmod(test_dir, 0o777)
        # Write the files under test
        # Do this first to prevent overwriting of included/instance files
        for name, contents in files_to_check.items():
            fpath = os.path.join(test_dir, name)
            with open(fpath, "wb") as fd:
                fd.write(base64.b64decode(contents))
            logger.info(f"Wrote file under test {fpath}")
            os.chmod(fpath, 0o664)

        # Write the exercise files required by this test
        for f_handle in required_files:
            f_resource = resources["checker_files"][f_handle]
            if f_resource["purpose"] not in ("INPUT", "WRAPPER", "TEST", "LIBRARY"):
                continue

            fpath = os.path.join(test_dir, f_resource["name"])
            with open(fpath, "wb") as fd:
                fd.write(base64.b64decode(f_resource["content"]))
            logger.info(f"Wrote required exercise file {fpath} from {f_handle}")
            os.chmod(fpath, chmod_parse(f_resource["chmod"]))

        all_json = True

        for stage in test["stages"]:
            stage_results, stage_json = run_stage(
                stage,
                test_dir,
                temp_dir_prefix,
                list(files_to_check.keys()),
            )
            test_results[test["test_id"]]["stages"][stage["id"]] = stage_results
            test_results[test["test_id"]]["stages"][stage["id"]]["name"] = stage["name"]
            test_results[test["test_id"]]["stages"][stage["id"]]["ordinal_number"] = stage[
                "ordinal"
            ]

            if not stage_json:
                all_json = False

            if stage_results["fail"]:
                break

        else:
            test_results[test["test_id"]]["fail"] = False

        # Run chmod on all files owned by the child process so that they can be cleaned up
        sec.chmod_child_files(test_dir)

    return test_results, all_json


@shared_task(name="courses.run-stage", bind=True)
def run_stage(self, stage, test_dir, temp_dir_prefix, files_to_check, revision=None):
    """

    Runs all the commands of this stage and collects the return values and the
    outputs.
    """

    all_json = True
    commands = stage["commands"]
    stage_results = {
        "fail": False,
        "commands": {},
    }

    if len(commands) == 0:
        return stage_results

    for command in commands:
        results = run_command_chainable(
            command,
            temp_dir_prefix,
            test_dir,
            files_to_check,
            stage_results=stage_results,
        )
        stage_results.update(results)

        if not command["json_output"]:
            all_json = False

        if results.get("fail"):
            stage_results["fail"] = True
            break

    return stage_results, all_json


@shared_task(name="courses.run-command-chain-block")
def run_command_chainable(command, temp_dir_prefix, test_dir, files_to_check, stage_results=None):
    if stage_results is None or "commands" not in stage_results.keys():
        stage_results = {"commands": {}}

    stdout = tempfile.TemporaryFile(dir=temp_dir_prefix)
    stderr = tempfile.TemporaryFile(dir=temp_dir_prefix)
    stdin = tempfile.TemporaryFile(dir=temp_dir_prefix)
    stdin.write(bytearray(command["input_text"], "utf-8"))
    stdin.seek(0)

    proc_results = run_command(
        command,
        stdin,
        stdout,
        stderr,
        test_dir,
        files_to_check,
    )

    stdout.seek(0)
    read_stdout = stdout.read()
    try:
        proc_results["stdout"] = read_stdout.decode("utf-8")
        proc_results["binary_stdout"] = False
    except UnicodeDecodeError as e:
        proc_results["stdout"] = cp437_decoder(read_stdout)
        proc_results["binary_stdout"] = True
    stdout.close()

    stderr.seek(0)
    read_stderr = stderr.read()
    try:
        proc_results["stderr"] = read_stderr.decode("utf-8")
        proc_results["binary_stderr"] = False
    except UnicodeDecodeError as e:
        proc_results["stderr"] = cp437_decoder(read_stderr)
        proc_results["binary_stderr"] = True
    stderr.close()

    if proc_results.get("fail"):
        stage_results["fail"] = True

    stage_results["commands"][command["ordinal"]] = proc_results

    return stage_results


@shared_task(name="courses.run-command")
def run_command(command, stdin, stdout, stderr, test_dir, files_to_check):
    """
    Runs the current command of this stage by automated fork & exec.
    """

    cmd = (
        command["cmd"]
        .replace("$RETURNABLES", " ".join(shlex.quote(f) for f in files_to_check))
        .replace("$CWD", test_dir)
    )
    timeout = command["timeout"]
    env = django_settings.CHECKING_ENV
    env["PWD"] = test_dir

    args = shlex.split(cmd)

    shell_like_cmd = " ".join(shlex.quote(arg) for arg in args)

    proc_results = {
        "ordinal_number": command["ordinal"],
        "expected_retval": command["return_value"],
        "input_text": command["input_text"],
        "significant_stdout": command["stdout"],
        "significant_stderr": command["stderr"],
        "json_output": command["json_output"],
        "command_line": shell_like_cmd,
    }
    logger.info(f"Running: {shell_like_cmd}")

    demote_process = sec.default_demote_process

    start_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start_time = time.time()
    try:
        proc = subprocess.Popen(
            args=args,
            bufsize=-1,
            executable=None,
            stdin=stdin,
            stdout=stdout,
            stderr=stderr,  # Standard fds
            preexec_fn=demote_process,  # Demote before fork
            start_new_session=True,
            close_fds=True,  # Don't inherit fds
            shell=False,  # Don't run in shell
            cwd=env["PWD"],
            env=env,
            universal_newlines=False,  # Binary stdout
        )
    except (FileNotFoundError, PermissionError) as e:
        # In case the executable is not found or permission to run the
        # file didn't exist.

        proc_results.update(
            {
                "retval": None,
                "timedout": False,
                "killed": False,
                "runtime": 0,
                "error": str(e),
                "fail": True,
            }
        )
        return proc_results

    proc_retval = None
    proc_timedout = False
    proc_killed = False

    try:
        proc.wait(timeout=timeout)
        proc_runtime = time.time() - start_time
        proc_retval = proc.returncode
    except subprocess.TimeoutExpired:
        proc_runtime = time.time() - start_time
        proc_retval = None
        proc_timedout = True
        if proc.poll() is None:
            sec.secure_kill(proc.pid)
            proc_killed = True

    proc_runtime = proc_runtime or (time.time() - start_time)
    proc_retval = proc_retval or proc.returncode
    # Collect statistics on CPU time consumed by the student's process
    # Consider implementing wait3 and wait4 for subprocess
    # http://stackoverflow.com/a/7050436/2096560
    end_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
    ru_utime = end_rusage.ru_utime - start_rusage.ru_utime
    ru_stime = end_rusage.ru_stime - start_rusage.ru_stime

    proc_results.update(
        {
            "retval": proc_retval,
            "timedout": proc_timedout,
            "killed": proc_killed,
            "runtime": proc_runtime,
            "usermodetime": ru_utime,
            "kernelmodetime": ru_stime,
        }
    )

    logger.info("\n".join(l.decode("utf-8") for l in stdout.readlines()))
    logger.info("\n".join(l.decode("utf-8") for l in stderr.readlines()))

    return proc_results


# ^
# |
# FILE EXERCISE CHECKING
# REPEATED TEMPLATE LEGACY STUFF
# |
# v


@shared_task(name="courses.precache-repeated-template-sessions", bind=True)
def precache_repeated_template_sessions(self):
    """
    Iterate through all repeated template exercises and ensure there's a buffer
    of pre-created sessions for each exercise in the database, waiting to be
    assigned to users.
    """

    exercises = cm.RepeatedTemplateExercise.objects.filter(
        content_type="REPEATED_TEMPLATE_EXERCISE"
    )

    ENSURE_COUNT = 10
    lang_codes = django_settings.LANGUAGES

    session_generator_chain = None
    for exercise in exercises:
        for lang_code, _ in lang_codes:
            sessions = cm.RepeatedTemplateExerciseSession.objects.filter(
                exercise=exercise, user=None, language_code=lang_code
            )
            generate_count = ENSURE_COUNT - sessions.count()
            logger.info(
                f"Exercise {exercise.name} with language {lang_code} missing "
                f"{generate_count} pre-generated sessions!"
            )
            exercise_generator = [
                generate_repeated_template_session.s(None, None, exercise.id, lang_code, 0)
                for _ in range(generate_count)
            ]

            if session_generator_chain is None:
                session_generator_chain = exercise_generator
            else:
                session_generator_chain = iterchain(session_generator_chain, exercise_generator)
    group(session_generator_chain).delay()


@shared_task(name="courses.generate-repeated-template-session", bind=True)
def generate_repeated_template_session(
    self, user_id, instance_id, exercise_id, lang_code, revision
):
    """
    Invoke the repeated template backend program to generate a session for a
    repeated template exercise. The session consists of multiple instances of
    parameters to fill in the template and the correct answers to accompany the
    generated parameters.

    Expects a conforming JSON in the stdout.
    """
    translation.activate(lang_code)

    exercise = cm.RepeatedTemplateExercise.objects.get(id=exercise_id)
    backend_files = cm.RepeatedTemplateExerciseBackendFile.objects.filter(exercise=exercise_id)
    command_m = cm.RepeatedTemplateExerciseBackendCommand.objects.get(exercise=exercise_id)

    if user_id is not None:
        user = User.objects.get(id=user_id)
    else:
        user = None

    # TODO: Also write some instance wide include files?

    args = shlex.split(command_m.command)

    # DEBUG
    timeout = 10
    # DEBUG

    temp_dir_prefix = os.path.join("/", "tmp")
    with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as generate_dir:
        for backend_file in backend_files:
            filename = backend_file.filename
            contents = backend_file.get_file_contents()
            backend_file_path = os.path.join(generate_dir, filename)
            with open(backend_file_path, "wb") as backend_fd:
                backend_fd.write(contents)

        stdout = tempfile.TemporaryFile(dir=generate_dir)
        stderr = tempfile.TemporaryFile(dir=generate_dir)

        env = {  # Remember that some information (like PATH) may come from other sources
            "PWD": generate_dir,
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "LC_CTYPE": "en_US.UTF-8",
        }

        logger.info("Running: {}".format(" ".join(shlex.quote(arg) for arg in args)))
        # TODO: Security aspects
        proc = subprocess.Popen(
            args=args,
            stdout=stdout,
            stderr=stderr,
            cwd=env["PWD"],
            env=env,
        )

        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.terminate()

        stdout.seek(0)
        try:
            output = stdout.read().decode("utf-8")
        except UnicodeDecodeError as e:
            raise e  # TODO

        stderr.seek(0)
        try:
            errors = stderr.read().decode("utf-8")
        except UnicodeDecodeError as e:
            raise e  # TODO
        stdout.close()
        stderr.close()

        logger.info("output", output)
        logger.info("errors", errors)

    try:
        output_json = json.loads(output)
        # TODO: https://python-jsonschema.readthedocs.io/en/latest/
    except json.decoder.JSONDecodeError as e:
        raise e  # TODO

    # Create the session, its instances and the associated answer choices
    with transaction.atomic():
        session = cm.RepeatedTemplateExerciseSession.objects.create(
            exercise=exercise,
            user=user,
            revision=0,  # revision, # TODO
            language_code=lang_code,
            generated_json=output_json,
        )
        session.save()

        if len(output_json["repeats"]) < 1:
            raise IntegrityError("No session instances generated! Rolling back.")

        for i, instance in enumerate(output_json["repeats"]):
            variables, values = zip(*instance["variables"].items())
            templates = cm.RepeatedTemplateExerciseTemplate.objects.filter(exercise=exercise_id)
            template = templates[random.randint(0, templates.count() - 1)]

            instance_obj = cm.RepeatedTemplateExerciseSessionInstance.objects.create(
                exercise=exercise,
                session=session,
                template=template,
                ordinal_number=i,
                variables=variables,
                values=values,
            )
            instance_obj.save()

            for answer in instance["answers"]:
                correct = answer["correct"]
                is_regex = answer["is_regex"]
                answer_str = answer["answer_str"]
                hint = answer.get("hint", "")
                comment = answer.get("comment", "")
                # triggers = answer.get('triggers', [])

                answer_obj = cm.RepeatedTemplateExerciseSessionInstanceAnswer.objects.create(
                    session_instance=instance_obj,
                    correct=correct,
                    regexp=is_regex,
                    answer=answer_str,
                    hint=hint,
                    comment=comment,
                    # triggers=triggers,
                )
                answer_obj.save()


# ^
# |
# REPEATED TEMPLATE LEGACY STUFF
# MISC
# |
# v


@shared_task(name="courses.deploy-backend", bind=True)
def deploy_backend(self, course, instance, source_path, target_name, lang, exercise=None):
    """
    Deploys an exercise backend file to a permanent location that's read-only
    for the student process during checking.
    """

    with open(source_path, "rb") as f:
        file_contents = f.read()

    deploy_root = django_settings.CHECKER_DEPLOYMENT_ROOT
    if exercise is None:
        path = os.path.join(deploy_root, instance, lang, target_name)
    else:
        path = os.path.join(deploy_root, instance, lang, exercise, target_name)

    os.makedirs(os.path.dirname(path), mode=0o775, exist_ok=True)

    with open(path, "wb") as f:
        f.write(file_contents)


def get_celery_worker_status():
    ERROR_KEY = "errors"
    try:
        from lovelace.celery import app as celery_app

        insp = celery_app.control.inspect()
        d = insp.stats()
        if not d:
            d = {ERROR_KEY: _("No running Celery workers were found.")}
    except IOError as e:
        from errno import errorcode

        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == "ECONNREFUSED":
            msg += " Check that the RabbitMQ server is running."
        d = {ERROR_KEY: msg}
    except Exception as e:
        d = {ERROR_KEY: "Uknown error: " + str(e)}
    return d
