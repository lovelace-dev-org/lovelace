from __future__ import absolute_import

import base64
import json
import logging
import os
import random
import resource
import shlex
import string
import subprocess
import tempfile
import time

from celery import shared_task
from django.conf import settings

from courses import evaluation_sec as sec

logger = logging.getLogger(__name__)

def _run_command(args, test_dir):
    # preparations to run the backend
    stdout = tempfile.TemporaryFile(dir=settings.TMP_PATH)
    stderr = tempfile.TemporaryFile(dir=settings.TMP_PATH)

    demote_process = sec.default_demote_process
    start_rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
    start_time = time.time()

    env = settings.CHECKING_ENV
    env["PWD"] = test_dir

    proc_results = {"command_line": " ".join(shlex.quote(arg) for arg in args)}

    # run the command in initialization mode
    try:
        proc = subprocess.Popen(
            args=args,
            bufsize=-1,
            executable=None,
            stdout=stdout,
            stderr=stderr,
            preexec_fn=demote_process,
            start_new_session=True,
            close_fds=True,
            shell=False,
            cwd=test_dir,
            env=env,
            universal_newlines=False,
        )
    except (FileNotFoundError, PermissionError) as e:
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
        proc.wait(timeout=10)
        proc_runtime = time.time() - start_time
        proc_retval = proc.returncode
    except subprocess.TimeoutExpired:
        proc_runtime = time.time() - start_time
        proc_retval = None
        proc_timedout = True
        if proc.poll() is None:
            sec.secure_kill(proc.pid)
            proc_killed = True


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

    stdout.seek(0)
    output = stdout.read()
    stderr.seek(0)
    errors = stderr.read()

    if errors:
        proc_results["fail"] = True
        proc_results["error"] = errors.decode("utf-8")
    else:
        try:
            proc_results["data"] = json.loads(output.decode("utf-8"))
        except json.JSONDecodeError as e:
            stderr.seek(0)
            proc_results["fail"] = True
            proc_results["error"] = str(e)

    return proc_results


@shared_task(name="routine_exercise.generate_question", bind=True)
def generate_question(self, payload):
    progress = payload["meta"]["progress"]

    with tempfile.TemporaryDirectory(dir=settings.TMP_PATH) as test_dir:
        os.chmod(test_dir, 0o777)

        # prepare backend files
        for backend in payload["resources"]["backends"]:
            fpath = os.path.join(test_dir, backend["name"])
            with open(fpath, "wb") as fd:
                fd.write(base64.b64decode(backend["content"]))
            logger.info(f"Wrote {backend['name' ]} from {backend['handle']}")
            os.chmod(fpath, 0o664)

        fn = "".join(random.choice(string.ascii_lowercase) for i in range(24)) + ".json"
        data = {
            "history": payload["meta"]["history"],
            "completed": payload["meta"]["completed"],
            "progress": progress,
        }
        with open(os.path.join(test_dir, fn), "w", encoding="utf-8") as f:
            json.dump(data, f)

        command = payload["command"]
        args = shlex.split(command)
        args.append("--request-params")
        args.append(fn)
        proc_results = _run_command(args, test_dir)

        sec.chmod_child_files(test_dir)

    if proc_results.get("fail") or proc_results.get("killed") or proc_results.get("timedout"):
        return {
            "task": "generate",
            "status": "fail",
            "error": proc_results["error"],
        }

    return {
        "task": "generate",
        "status": "success",
        "data": proc_results["data"],
    }


@shared_task(name="routine_exercise.check_answer", bind=True)
def check_answer(self, payload):
    answer = payload["answer"]
    progress = payload["meta"]["progress"]

    with tempfile.TemporaryDirectory(dir=settings.TMP_PATH) as test_dir:
        os.chmod(test_dir, 0o777)

        # prepare backend files
        for backend in payload["resources"]["backends"]:
            fpath = os.path.join(test_dir, backend["name"])
            with open(fpath, "wb") as fd:
                fd.write(base64.b64decode(backend["content"]))
            logger.info(f"Wrote {backend['name']} from {backend['handle']}")
            os.chmod(fpath, 0o664)

        fn = "".join(random.choice(string.ascii_lowercase) for i in range(24)) + ".json"
        data = {
            "answer": answer,
            "question_class": payload["question"]["class"],
            "params": payload["question"]["data"],
            "history": payload["meta"]["history"],
            "completed": payload["meta"]["completed"],
            "progress": progress,
        }
        with open(os.path.join(test_dir, fn), "w", encoding="utf-8") as f:
            json.dump(data, f)

        command = payload["command"]
        args = shlex.split(command)
        args.append("--check")
        args.append(fn)
        proc_results = _run_command(args, test_dir)

        sec.chmod_child_files(test_dir)

    if proc_results.get("timedout"):
        return {
            "task": "check",
            "status": "timeout",
            "error": proc_results["error"],
        }
    if proc_results.get("fail") or proc_results.get("killed"):
        return {
            "task": "check",
            "status": "fail",
            "error": proc_results["error"],
        }
    return {
        "task": "check",
        "status": "success",
        "data": proc_results["data"],
    }
