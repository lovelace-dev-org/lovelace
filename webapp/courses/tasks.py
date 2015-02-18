"""
Celery tasks for checking a user's answers to file upload, code input and code
replace exercises.
"""
# TODO: Implement tests for ranked code exercises and group code exercises.
from __future__ import absolute_import

from collections import namedtuple
from django.contrib.auth.models import User

import json

# Test dependencies
import tempfile
import os
import random

# Stage dependencies
import base64

# Command dependencies
import time
import shlex
import subprocess

from celery import shared_task, chain

# The test data
#from courses.models import FileExerciseTest, FileExerciseTestStage,\
    #FileExerciseTestCommand, FileExerciseTestExpectedOutput,\
    #FileExerciseTestIncludeFile
#from courses.models import CodeInputExerciseAnswer # code input exercise models
#from courses.models import CodeReplaceExerciseAnswer # code replace exercise models
#from courses.models import # ranked code exercise models
#from courses.models import # group code exercise models

# The users' answers
#from courses.models import UserFileUploadExerciseAnswer,\
    #FileUploadExerciseReturnFile

import courses.models

@shared_task(name="courses.run-fileexercise-tests", bind=True)
def run_tests(self, user_id, exercise_id, answer_id):
    # TODO: Actually, just receive the relevant ids for fetching the Django
    #       models here instead of in the Django view.
    # http://celery.readthedocs.org/en/latest/userguide/tasks.html#database-transactions

    #def run_tests(tests, test_files, student_files, reference_files):
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
    # TODO: Input generator targets:
    #       - stdin
    #       - readable file
    #       - as command line parameters!
    #       - in env?

    try:
        exercise_object = courses.models.FileUploadExercise.objects.get(id=exercise_id)
    except courses.models.FileUploadExercise.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user

    self.update_state(state="PROGRESS", meta={"current":4, "total":10})
    user_object = User.objects.get(id=user_id)
    print("user: %s" % (user_object.username))
    #x = [i for i in range(10**8) if i % 2 == 1]
    #return

    
    # Get the test data
    # TODO: Use prefetch_related?
    
    tests = courses.models.FileExerciseTest.objects.filter(exercise=exercise_id)

    student_results = {}
    reference_results = {}
    
    # Run all the tests for both the returned and reference code
    for i, test in enumerate(tests):
        self.update_state(state="PROGRESS", meta={"current": i, "total": len(tests)})

        # TODO: The student's code can be run in parallel with the reference
        results = run_test(test.id, answer_id, exercise_id, student=True)
        student_results.update(results)
        results = run_test(test.id, answer_id, exercise_id)
        reference_results.update(results)

    print(student_results.items())
    print(reference_results.items())

    results = {"student": student_results, "reference": reference_results}

    # TODO: Make the comparisons to determine correct status
    # Ultimate encoding: http://en.wikipedia.org/wiki/Code_page_437

    # Determine the result and generate JSON accordingly
    # Save the rendered results into Redis
    result_string = json.dumps(results)

    # Save the results to database
    evaluation = courses.models.Evaluation(test_results=result_string)
    evaluation.save()
    try:
        answer_object = courses.models.UserFileUploadExerciseAnswer.objects.get(id=answer_id)
    except courses.models.UserFileUploadExerciseAnswer.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user
    answer_object.evalution = evaluation
    answer_object.save()

    return evaluation.id
    
    # TODO: Should we:
    # - return the results? (most probably not)
    # - save the results directly into db? (is this worker contained enough?)
    # - send the results to a more privileged Celery worker for saving into db?

@shared_task(name="courses.run-test", bind=True)
def run_test(self, test_id, answer_id, exercise_id, student=False):
    """
    Runs all the stages of the given test.
    """
    try:
        test = courses.models.FileExerciseTest.objects.get(id=test_id)
    except courses.models.FileExerciseTest.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user

    try:
        stages = courses.models.FileExerciseTestStage.objects.filter(test=test_id)
    except courses.models.FileExerciseTestStage.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user

    try:
        exercise_file_objects = courses.models.FileExerciseTestIncludeFile.objects.filter(exercise=exercise_id)
    except courses.models.FileExerciseTestIncludeFile.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user

    # Note: requires a shared/cloned file system!
    if student:
        try:
            answer_object = courses.models.UserFileUploadExerciseAnswer.objects.get(id=answer_id)
        except courses.models.UserFileUploadExerciseAnswer.DoesNotExist as e:
            # TODO: Log weird request
            return # TODO: Find a way to signal the failure to the user
        
        files_to_check = answer_object.get_returned_files()
        print("".join("%s:\n%s" % (n, c) for n, c in files_to_check.items()))
    else:
        files_to_check = {f.get_filename(): f.get_file_contents()
                          for f in exercise_file_objects
                          if f.purpose == "REFERENCE"}
        print("".join("%s:\n%s" % (n, c) for n, c in files_to_check.items()))

    # TODO: Replace with the directory of the ramdisk
    temp_dir_prefix = os.path.join("/", "tmp")

    test_results = {test_id: {"fail": True}}
    with tempfile.TemporaryDirectory(dir=temp_dir_prefix) as test_dir:
        # Write the files required by this test
        for name, contents in ((f.get_filename(), f.get_file_contents)
                               for f in exercise_file_objects
                               if f in test.required_files.all() and
                               f.purpose in ("INPUT", "WRAPPER", "TEST")):
            fpath = os.path.join(test_dir, name)
            with open(fpath, "wb") as fd:
                fd.write(contents)
            print("Wrote required test file %s" % (fpath))
            # TODO: chmod, chown, chgrp

        # Write the files under test
        for name, contents in files_to_check.items():
            fpath = os.path.join(test_dir, name)
            with open(fpath, "wb") as fd:
                fd.write(contents)
            print("Wrote file under test %s" % (fpath))
            # TODO: chmod, chown, chgrp

        # TODO: Replace with chaining
        for i, stage in enumerate(stages):
            #self.update_state(state="PROGRESS",
                              #meta={"current": i, "total": len(stages)})
            
            stage_results = run_stage(stage.id, test_dir, temp_dir_prefix,
                                      list(files_to_check.keys()))
            test_results[test_id].update(stage_results)

            if stage_results["fail"] == True:
                break

            # TODO: Read the directory and save the stage results in cache
            cache_results = False # TODO: Determine this by looking at dependencies
            if cache_results == True:
                test_dir_contents = os.listdir(test_dir)
                for fp in test_dir_contents:
                    with open(fp, "rb") as fd:
                        contents = fd.read()
        else:
            test_results[test_id]["fail"] = False

        # TODO: Read the expected output files (check the cache first?)
        test_dir_contents = os.listdir(test_dir)

    return test_results

@shared_task(name="courses.run-stage", bind=True)
def run_stage(self, stage_id, test_dir, temp_dir_prefix, files_to_check):
    """
    Runs all the commands of this stage and collects the return values and the
    outputs.
    """

    try:
        commands = courses.models.FileExerciseTestCommand.objects.filter(stage=stage_id)
    except courses.models.FileExerciseTestCommand.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user

    stage_results = {"fail": False}

    if len(commands) == 0:
        return stage_results

    
    cmd_chain = chain(run_command_chainable.s(cmd, temp_dir_prefix, test_dir, files_to_check)
                      for cmd in commands)

    try:
        results = cmd_chain().get()
    except:
        stage_results["fail"] = True

    stage_results.update(results)

    return stage_results
    
    """
    for i, cmd in enumerate(commands):
        stage_results[cmd.id] = {}
        #self.update_state(state="PROGRESS",
                          #meta={"current-stage": i, "total-stage": len(commands)})
        
        # Create the outputs and inputs outside the test directory, thereby
        # effectively hiding them from unskilled users.
        stdout = tempfile.TemporaryFile(dir=temp_dir_prefix)
        stderr = tempfile.TemporaryFile(dir=temp_dir_prefix)
        stdin = tempfile.TemporaryFile(dir=temp_dir_prefix)
        stdin.write(bytearray(cmd.input_text, "utf-8"))

        proc_results = run_command(cmd.id, stdin, stdout, stderr, test_dir, files_to_check)
        stage_results[cmd.id].update(proc_results)

        stdout.seek(0)
        stage_results[cmd.id]["stdout"] = base64.standard_b64encode(stdout.read()).decode("ASCII")
        stdout.close()
        stderr.seek(0)
        stage_results[cmd.id]["stderr"] = base64.standard_b64encode(stderr.read()).decode("ASCII")
        stderr.close()

        # If the command failed, abort the stage
        if cmd.return_value is not None and cmd.return_value != proc_results["retval"]:
            break
        #if cmd.expected.stdout != stage_results[cmd.id]["stdout"]:
            #break
        #if cmd.expected.stderr != stage_results[cmd.id]["stderr"]:
            #break
    else:
        stage_results["fail"] = False
    """

    # determine if the stage fails
    # if the stage fails, we can abort the tests/stages dependent on this stage
    # IDEA: stages are defined to be used by any test making those tests run or
    #       use the cached result of that stage
    #       - possible pitfall: same command, e.g. python student.py
    #         interpreted as "same stage"
    # IDEA: each stage can define a stage they depend on, making a directed
    #       graph of dependent stages

    return stage_results

@shared_task(name="courses.run-command-chain-block")
def run_command_chainable(cmd, temp_dir_prefix, test_dir, files_to_check, stage_results=None):
    if stage_results is None:
        stage_results = {}
    stage_results[cmd.id] = {}

    stdout = tempfile.TemporaryFile(dir=temp_dir_prefix)
    stderr = tempfile.TemporaryFile(dir=temp_dir_prefix)
    stdin = tempfile.TemporaryFile(dir=temp_dir_prefix)
    stdin.write(bytearray(cmd.input_text, "utf-8"))
    
    proc_results = run_command(cmd.id, stdin, stdout, stderr, test_dir, files_to_check)
    
    stdout.seek(0)
    proc_results["stdout"] = base64.standard_b64encode(stdout.read()).decode("ASCII")
    stdout.close()
    stderr.seek(0)
    proc_results["stderr"] = base64.standard_b64encode(stderr.read()).decode("ASCII")
    stderr.close()

    stage_results[cmd.id].update(proc_results)

    if cmd.return_value is not None and cmd.return_value != proc_results["retval"]:
        raise Exception()

    return stage_results

@shared_task(name="courses.run-command")
def run_command(cmd_id, stdin, stdout, stderr, test_dir, files_to_check):
    """
    Runs the current command of this stage by automated fork & exec.
    """
    try:
        command = courses.models.FileExerciseTestCommand.objects.get(id=cmd_id)
    except courses.models.FileExerciseTestCommand.DoesNotExist as e:
        # TODO: Log weird request
        return # TODO: Find a way to signal the failure to the user

    to_secs = lambda hour, minute, second, µsecond: ((hour * 60 + minute) * 60)\
              + second + (µsecond * 0.000001)

    cmd = command.command_line.replace("$RETURNABLES", " ".join(files_to_check))
    timeout = to_secs(command.timeout.hour, command.timeout.minute,
                      command.timeout.second, command.timeout.microsecond)
    env = {"PWD": test_dir}
    args = shlex.split(cmd)

    print("Running: %s" % (shlex.quote(" ".join(args))))

    start_time = time.time()
    proc = subprocess.Popen(args=args, bufsize=-1, executable=None,
                            stdin=stdin, stdout=stdout, stderr=stderr, # Standard fds
                            #preexec_fn=demote_process,                 # Demote before fork
                            close_fds=True,                            # Don't inherit fds
                            shell=False,                               # Don't run in shell
                            cwd=env["PWD"], env=env,
                            universal_newlines=False)                  # Binary stdout
    
    proc_retval = None
    proc_timedout = False
    
    try:
        proc.wait(timeout=timeout)
        proc_runtime = time.time() - start_time
        proc_retval = proc.returncode
    except subprocess.TimeoutExpired:
        proc_timedout = True
        proc.terminate() # Try terminating the process nicely
        time.sleep(0.5)
        
    # Clean up by halting all action (forking etc.) by the student's process
    # with SIGSTOP and by killing the frozen processes with SIGKILL

    # ...or maybe kill -SIGKILL -1 with the student's credentials? No.

    proc_runtime = proc_runtime or (time.time() - start_time)
    proc_retval = proc_retval or proc.returncode
    proc_results = {"retval": proc_retval, "timedout": proc_timedout,
                    "runtime": proc_runtime}

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
    ERROR_KEY = "errors"
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
