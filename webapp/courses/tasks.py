# Celery tasks
from __future__ import absolute_import
import time
import shlex
import subprocess
from collections import namedtuple

from celery import shared_task

from time import sleep

@shared_task
def add(x, y):
    return x + y


@shared_task
def mul(x, y):
    return x * y

@shared_task
def xsum(numbers):
    sleep(10)
    return sum(numbers)

@shared_task(name="courses.run-filetask-test")
def run_tests(tests, test_files, student_files, reference_files):
    # tests: the metadata for all the tests
    # test_files: the files that are integral for the tests
    # student_files: the files the student uploaded - these will be tested
    # reference_files: the reference files - these will be tested the same way
    #                  as the student's files


    exercise_results = (1, 2, 3, "moi")

    # Should we:
    # - return the results?
    # - save the results directly into db?
    # - send the results to a more privileged Celery worker for saving into db?
    # DEBUG: As a development stage measure, just return the result:
    return exercise_results

@shared_task(name="courses.run-stage")
def run_stage(cmds):
    """
    Runs all the commands of this stage and collects the return values and the
    outputs.
    """
    for cmd in cmds:
        run_command(cmd)

    # determine if the stage fails

    return stage_results

@shared_task(name="courses.run-command")
def run_command(cmd, env, stdin, stdout, stderr, timeout):
    """
    Runs the current command of this stage by automated fork & exec.
    """
    env = {}
    #cmd = shlex.split(cmd)
    #start_time = time.time()
    #proc = Popen(...)

    #proc_runtime = time.time() - start_time

    # For this function's return value:
    proc_retval = 0
    proc_timedout = False
    proc_runtime = 0.0

    proc_results = (proc_retval, proc_timedout, proc_runtime)

    return proc_results

    #return namedtuple()

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
