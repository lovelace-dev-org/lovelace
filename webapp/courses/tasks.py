"""
Celery tasks for checking the File Exercise files returned by the student.
"""
from __future__ import absolute_import

from collections import namedtuple

# Test dependencies
import tempfile
import os

# Command dependencies
import time
import shlex
import subprocess

from celery import shared_task

@shared_task
def add(x, y):
    return x + y

@shared_task(name="courses.run-filetask-tests")
def run_tests(tests, test_files, student_files, reference_files):
    # TODO: Actually, just receive the relevant ids for fetching the Django
    #       models here instead of in the Django view.
    # http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions

    # tests: the metadata for all the tests
    # test_files: the files that are integral for the tests
    # student_files: the files the student uploaded - these will be tested
    # reference_files: the reference files - these will be tested the same way
    #                  as the student's files

    # TODO: Check if any input generators are used. If yes, find a way to supply
    #       the same generated input to both the student's and reference codes.
    #       Some possibilities:
    #       - Generate a seed _here_ and pass it on (wastes CPU time?)
    #       - Generate the inputs _here_ and pass them on (best guess)
    #       - Generate the inputs during the code evaluation process and have
    #         the other code set depend on them (complicated to implement)

    student_results = {}
    reference_results = {}
    
    for i, test in enumerate(tests):
        current_task.update_state(state="PROGRESS",
                                  meta={"current":i, "total":len(tests)})

        # TODO: The student's code can be run in parallel with the reference
        student_test_results = run_test(test, test_files, student_files)
        reference_test_results = run_test(test, test_files, reference_files)

    exercise_results = ["lol", "FIX", student_results, reference_results]
    
    # TODO: Should we:
    # - return the results? (most probably not)
    # - save the results directly into db? (is this worker contained enough?)
    # - send the results to a more privileged Celery worker for saving into db?
    # DEBUG: As a development stage measure, just return the result:
    return exercise_results

@shared_task(name="courses.run-test")
def run_test(test, test_files, files_to_check):
    """
    Runs all the stages of the given test.
    """
    # Replace with the directory of the ramdisk
    temp_dir_prefix = os.path.join("/", "tmp")

    test_results = {}
    with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as test_dir:
        # Write the files required by this test
        for fp in (test_files[fp] for fp in test.required_test_files):
            fpath = os.path.join(test_dir, fp.filename)
            with open(fpath, "wb") as fd:
                fd.write(fp.contents)
            # TODO: chmod, chown, chgrp

        # Write the files under test
        for fp in files_to_check:
            fpath = os.path.join(test_dir, fp.filename)
            with open(fpath, "wb") as fd:
                fd.write(fp.contents)
            # TODO: chmod, chown, chgrp    

        # TODO: Replace with chaining
        for i, stage in enumerate(test.stages):
            current_task.update_state(state="PROGRESS",
                                      meta={"current":i,
                                            "total":len(test.stages)})
            
            stage_results = run_stage(stage.cmds)

            if stage_results["fail"] == True:
                break

            # TODO: Read the directory and save the stage results in cache
            if stage.cache_results == True:
                test_dir_contents = os.listdir(test_dir)
                for fp in test_dir_contents:
                    with open(fp, "rb") as fd:
                        contents = fd.read()
        else:
            test_results["fail"] == True

        # TODO: Read the expected output files
        test_dir_contents = os.listdir(test_dir)
        

    return test_results

@shared_task(name="courses.run-stage")
def run_stage(cmds, temp_dir_prefix):
    """
    Runs all the commands of this stage and collects the return values and the
    outputs.
    """

    stage_results = {}

    # TODO: Replace with chaining
    for i, cmd in enumerate(cmds):
        current_task.update_state(state="PROGRESS",
                                  meta={"current":i, "total":len(cmds)})
        
        stdout = tempfile.TemporaryFile(dir=temp_dir_prefix)
        stderr = tempfile.TemporaryFile(dir=temp_dir_prefix)
        stdin = tempfile.TemporaryFile(dir=temp_dir_prefix)
        stdin.write(cmd.stdin)

        proc_results = run_command(cmd)

        stdout.seek(0)
        stage_results[cmd].stdout = stdout.read()
        stdout.close()
        stderr.seek(0)
        stage_results[cmd].stderr = stderr.read()
        stderr.close()

        # If the command failed, abort the stage
        if cmd.expected.retval != proc_results.retval:
            break
        if cmd.expected.stdout != stage_results[cmd].stdout:
            break
        if cmd.expected.stderr != stage_results[cmd].stderr:
            break
    else:
        stage_results["fail"] = True

    # determine if the stage fails
    # if the stage fails, we can abort the tests/stages dependent on this stage
    # IDEA: stages are defined to be used by any test making those tests run or
    #       use the cached result of that stage
    #       - possible pitfall: same command, e.g. python student.py
    #         interpreted as "same stage"
    # IDEA: each stage can define a stage they depend on, making a directed
    #       graph of dependent stages

    return stage_results

@shared_task(name="courses.run-command")
def run_command(cmd, env, stdin, stdout, stderr, timeout):
    """
    Runs the current command of this stage by automated fork & exec.
    """
    env = {}
    args = shlex.split(cmd)
    cwd = env["PWD"]
    start_time = time.time()
    proc = Popen(args=args, bufsize=-1, executable=None,
                 stdin=stdin, stdout=stdout, stderr=stderr, # Standard fds
                 preexec_fn=demote_process,                 # Demote before fork
                 close_fds=True,                            # Don't inherit fds
                 shell=False,                               # Don't run in shell
                 cwd=cwd, env=env,
                 univeral_newlines=False)                   # Binary stdout
    
    proc_retval = None
    proc_timedout = False
    try:
        proc.wait(timeout=timeout)
        proc_runtime = time.time() - start_time
        proc_retval = proc.returncode
    except TimeoutExpired:
        proc_timedout = True
        proc.terminate() # Try terminating the process nicely
        time.sleep(0.5)
        
    # Clean up by halting all action (forking etc.) by the student's process
    # with SIGSTOP and by killing the frozen processes with SIGKILL

    # ...or maybe kill -SIGKILL -1 with the student's credentials?

    proc_runtime = proc_runtime or (time.time() - start_time)
    proc_retval = proc_retval or proc.returncode
    proc_results = (proc_retval, proc_timedout, proc_runtime)

    return proc_results

# TODO: Subtask division:
#       - Run all tests:
#           * individual tests for the student's program
#           * chainable stages (e.g. save the results of compilation, and then
#             use these results for each of the tests)
#           * dependent stages (e.g. must pass compilation to even try running)
#       - Run all reference program tests
#           * stages that depend on student's test stage success (no need run
#             if student's code fails to compile etc.)
#           * cacheable reference tests results
#               o checkbox for marking whether the results _can_ be cached
#                 (e.g. using an input generator prevents reference result
#                  caching -> automatically disable checkbox)
#       - Calculate the diffs in between the tests
#           * correct/failed status for individual tests!

# TODO: Progress checking!
#       - which subtasks have been completed
#       - how many tests have failed, how many have been correct
#       - how many and what kind are left

# TODO: Celery worker status checking:
# http://stackoverflow.com/questions/8506914/detect-whether-celery-is-available-running
def get_celery_worker_status():
    ERROR_KEY = "ERROR"
    try:
        from celery.task.control import inspect
        insp = inspect()
        d = insp.stats()
        if not d:
            d = { ERROR_KEY: 'No running Celery workers were found.' }
    except IOError as e:
        from errno import errorcode
        msg = "Error connecting to the backend: " + str(e)
        if len(e.args) > 0 and errorcode.get(e.args[0]) == 'ECONNREFUSED':
            msg += ' Check that the RabbitMQ server is running.'
        d = { ERROR_KEY: msg }
    except ImportError as e:
        d = { ERROR_KEY: str(e)}
    return d
