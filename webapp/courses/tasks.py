# Celery tasks
from __future__ import absolute_import

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
def run_test(test_data):
    return "lollerolle-lol"

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
