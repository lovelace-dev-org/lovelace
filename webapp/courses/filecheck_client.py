# -*- coding: utf-8 -*-
"""
Module for connecting to the file checking bot on a remote machine using JSON-RPC and generating HTML
from the test results.
"""

import difflib
import datetime
import base64
import pipes
from cgi import escape

# Testing related data
from courses.models import FileExerciseTest
from courses.models import FileExerciseTestIncludeFile
from courses.models import FileExerciseTestStage, FileExerciseTestCommand
from courses.models import FileExerciseTestExpectedOutput

# Given answer related data
from courses.models import FileUploadExerciseReturnFile

import courses.tasks as rpc_tasks


def check_file_answer(exercise, files={}, answer=None):
    test_object = compose_test_object(exercise)
    result = rpc_tasks.run_tests.delay(test_object, 2, 3, 4)

    print(result.task_id)

    return result.task_id


def compose_test_object(exercise):
    """
    Get the exercise related tests from the database and compose an easily
    readable object of them for the Celery task.
    """
    test_object = {}
    # TODO: Use select_related to speed up the queries
    db_tests = FileExerciseTest.objects.filter(exercise=exercise)
    for db_test in db_tests:
        db_stages = FileExerciseTestStage.objects.filter(test=db_test)
        for db_stage in db_stages:
            db_cmds = FileExerciseTestCommand.objects.filter(stage=db_stage)
            for db_cmd in db_cmds:
                db_outputs = FileExerciseTestExpectedOutput.objects.filter(command=db_cmd)

    return test_object


def file_exercise_check(content, user, files_data, post_data):
    # NOTE: Deprecated code moved from views.py to here temporarily.
    points = 0.0
    correct = True
    hints = []
    comments = []

    # TODO: Create a model manager that fetches all relevant information
    #       for the file exercise in question.
    # TODO: Fetch all the relevant information using the above manager.
    # TODO: Cache it to save many complicated db queries and filesystem reads.

    if user.is_authenticated() and points == 666.6:
        # TODO: Fix the information that will be saved
        f_returnable = FileTaskReturnable(
            run_time=datetime.time(0, 0, 1, 500),
            output="filler-output-filler",
            errors="filler-errors-filler",
            retval=0,
        )
        f_returnable.save()
        f_evaluation = Evaluation(points=points, feedback="", correct=False)
        f_evaluation.save()
        if "collaborators" in post_data.keys():
            collaborators = post_data["collaborators"]
        else:
            collaborators = None
        f_answer = UserFileTaskAnswer(
            exercise=content.exercisepage.filetask,
            returnable=f_returnable,
            evaluation=f_evaluation,
            user=user,
            answer_date=timezone.now(),
            collaborators=collaborators,
        )
        f_answer.save()

        for entry_name, uploaded_file in files_data.items():
            f_filetaskreturnfile = FileTaskReturnFile(
                fileinfo=uploaded_file, returnable=f_returnable
            )
            f_filetaskreturnfile.save()

        results = filecheck_client.check_file_answer(
            exercise=content.exercisepage.filetask, files={}, answer=f_answer
        )

        # Quickly determine, whether the answer was correct
        results_zipped = []
        student_results = []
        reference_results = []
        ref = ""
        if "reference" in results.keys():
            ref = "reference"
        elif "expected" in results.keys():
            ref = "expected"

        for test in results["student"].keys():
            # TODO: Do the output and stderr comparison here instead of below
            results_zipped.append(
                zip(results["student"][test]["outputs"], results[ref][test]["outputs"])
            )
            results_zipped.append(
                zip(results["student"][test]["errors"], results[ref][test]["errors"])
            )

            for name, content in results[ref][test]["outputfiles"].items():
                if name not in results["student"][test]["outputfiles"].keys():
                    correct = False
                else:
                    if content != results["student"][test]["outputfiles"][name]:
                        correct = False

        for test in results_zipped:
            for resultpair in test:
                if resultpair[0].replace("\r\n", "\n") != resultpair[1].replace("\r\n", "\n"):
                    correct = False

        if correct:
            f_evaluation.points = 1.0
            f_evaluation.correct = correct
            f_evaluation.save()
            f_answer.save()
    elif points == 555.5:
        files = {}
        for rf in files_data.values():
            f = bytes()
            for chunk in rf.chunks():
                f += chunk
            files[rf.name] = f
        results = filecheck_client.check_file_answer(
            exercise=content.exercisepage.filetask, files=files
        )

        # Quickly determine, whether the answer was correct
        results_zipped = []
        student_results = []
        reference_results = []
        ref = ""
        if "reference" in results.keys():
            ref = "reference"
        elif "expected" in results.keys():
            ref = "expected"

        for test in results["student"].keys():
            # TODO: Do the output and stderr comparison here instead of below
            results_zipped.append(
                zip(results["student"][test]["outputs"], results[ref][test]["outputs"])
            )
            results_zipped.append(
                zip(results["student"][test]["errors"], results[ref][test]["errors"])
            )

            for name, content in results[ref][test]["outputfiles"].items():
                if name not in results["student"][test]["outputfiles"].keys():
                    correct = False
                else:
                    if content != results["student"][test]["outputfiles"][name]:
                        correct = False

        for test in results_zipped:
            for resultpair in test:
                if resultpair[0].replace("\r\n", "\n") != resultpair[1].replace("\r\n", "\n"):
                    correct = False

    # Get a nice HTML table for the diffs
    # diff_table = filecheck_client.html(results)
    results = filecheck_client.check_file_answer(1, 2, 3)
    diff_table = results

    return correct, hints, comments, diff_table


def ex_check_file_answer(task, files={}, answer=None):
    """Iterates through all the tests for a returnable package of user content."""
    print("Checking a file")
    _secs = lambda dt: dt.hour * 3600 + dt.minute * 60 + dt.second

    # Read the returned files from database objects
    if answer:
        ft_returned_files = FileTaskReturnFile.objects.filter(returnable=answer.returnable)
        codefiles = {}
        for ft_returned_file in ft_returned_files:
            with open(ft_returned_file.fileinfo.path, "rb") as f:
                codefiles[ft_returned_file.filename()] = f.read()
    else:
        codefiles = files

    # Construct the tests from database objects
    ft_tests = FileTaskTest.objects.filter(task=task)
    tests = list()
    references = dict()
    expected = dict()
    for ft_test in ft_tests:
        ft_test_name = ft_test.name

        ft_test_timeout = ft_test.timeout

        ft_test_signal = ft_test.signals

        ft_test_input = ft_test.inputs

        ft_test_commands = FileTaskTestCommand.objects.filter(test=ft_test)
        commands = [(tc.command_line, tc.main_command) for tc in ft_test_commands] or [""]

        ft_test_expected_outputs = FileTaskTestExpectedOutput.objects.filter(test=ft_test)
        outputs = [eo.expected_answer for eo in ft_test_expected_outputs] or [""]

        ft_test_expected_errors = FileTaskTestExpectedError.objects.filter(test=ft_test)
        errors = [ee.expected_answer for ee in ft_test_expected_errors] or [""]

        ft_test_include_files = FileTaskTestIncludeFile.objects.filter(test=ft_test)
        include_files = {}
        inputgens = {}
        unittests = {}
        input_files = {}
        output_files = {}
        for ft_test_include_file in ft_test_include_files:
            filename = ft_test_include_file.name
            with open(ft_test_include_file.fileinfo.path, "rb") as f:
                include_files[filename] = base64.b64encode(f.read())
            if ft_test_include_file.purpose == "REFERENCE":
                references[filename] = include_files[filename]
            elif ft_test_include_file.purpose == "INPUTGEN":
                inputgens[filename] = include_files[filename]
            elif ft_test_include_file.purpose == "TEST":
                unittests[filename] = include_files[filename]
            elif ft_test_include_file.purpose == "INPUT":
                input_files[filename] = include_files[filename]
            elif ft_test_include_file.purpose == "OUTPUT":
                output_files[filename] = include_files[filename]

        test = {
            "name": ft_test_name,
            "timeout": _secs(ft_test_timeout),
            "signal": ft_test_signal,
            "args": commands,
            "unittests": unittests,
            "inputgens": inputgens,
            "input": ft_test_input,
            "inputfiles": input_files,
            "output": outputs,
            "outputfiles": output_files,
            "errors": errors,
        }
        tests.append(test)
        expected[ft_test_name] = {
            "outputs": outputs,
            "outputfiles": output_files,
            "errors": errors,
        }

    results = None

    # Encode into base64 in order to avoid trouble
    for name, contents in codefiles.items():
        codefiles[name] = base64.b64encode(contents)

    # Send the tests and files to the checking server and receive the results
    bjsonrpc_client = bjsonrpc.connect(host="10.10.110.66", port=10123)

    if references:
        results = bjsonrpc_client.call.checkWithReference(codefiles, references, tests)
        bjsonrpc_client.close()

        for test_name, test_result in results["reference"].items():
            test_result["outputs"] = [base64.b64decode(output) for output in test_result["outputs"]]
            test_result["errors"] = [base64.b64decode(error) for error in test_result["errors"]]
            for output_file_name, output_file_contents in test_result["outputfiles"].items():
                test_result["outputfiles"][output_file_name] = base64.b64decode(
                    output_file_contents
                )
            for input_file_name, input_file_contents in test_result["inputfiles"].items():
                test_result["inputfiles"][input_file_name] = base64.b64decode(input_file_contents)
    else:
        results = bjsonrpc_client.call.checkWithOutput(codefiles, tests)
        bjsonrpc_client.close()
        results["expected"] = expected

    for test_name, test_result in results["student"].items():
        test_result["outputs"] = [base64.b64decode(output) for output in test_result["outputs"]]
        test_result["errors"] = [base64.b64decode(error) for error in test_result["errors"]]
        for output_file_name, output_file_contents in test_result["outputfiles"].items():
            test_result["outputfiles"][output_file_name] = base64.b64decode(output_file_contents)
        for input_file_name, input_file_contents in test_result["inputfiles"].items():
            test_result["inputfiles"][input_file_name] = base64.b64decode(input_file_contents)

    print("File checked")

    return results


def html(results):
    colgroup_old = "<colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>\n        <colgroup></colgroup> <colgroup></colgroup> <colgroup></colgroup>"
    colgroup_new = """<colgroup class="student"><col class="lnum" span="2" /><col class="content" />
</colgroup><colgroup class="expected"><col class="lnum" span="2"><col class="content" /></colgroup>"""
    diff_tables = "<h1>Test results</h1>\n"
    expected = None
    reference = None
    for test_name, test_result in results["student"].items():
        # TODO: Use templates instead!
        diff_tables += "<h2>Test: %s</h2>\n" % (escape(str(test_name.decode("utf-8"))))
        if "reference" in results.keys():
            reference = results["reference"][test_name]
        elif "expected" in results.keys():
            expected = results["expected"][test_name]

        if test_result["input"]:
            diff_tables += '<h3>Input:</h3>\n<pre class="normal">%s</pre>\n' % (
                escape(str(test_result["input"].decode("utf-8")))
            )
        if test_result["inputfiles"]:
            for inputfile, contents in test_result["inputfiles"].items():
                diff_tables += '<h3>Input file: %s</h3>\n<pre class="normal">%s</pre>\n' % (
                    escape(str(inputfile.decode("utf-8"))),
                    escape(contents),
                )

        for i, cmd in enumerate(test_result["cmds"]):
            diff_tables += '<h3>Command: <span class="command">%s</span></h3>\n' % (
                str(" ".join(pipes.quote(s) for s in cmd[0]).decode("utf-8"))
            )  # (cmd[0])

            rcv_retval = test_result["returnvalues"][i]
            rcv_output = test_result["outputs"][i].split("\n")
            rcv_error = test_result["errors"][i].split("\n")

            if reference:
                exp_retval = reference["returnvalues"][i]
                exp_output = reference["outputs"][i].split("\n")
                exp_error = reference["errors"][i].split("\n")
            elif expected:
                if cmd[1]:
                    exp_retval = 0
                    exp_output = str(expected["outputs"][0].decode("utf-8")).split("\n")
                    exp_error = str(expected["errors"][0].decode("utf-8")).split("\n")
                else:
                    exp_retval = 0
                    exp_output = [str()]
                    exp_error = [str()]

            out_diff = (
                difflib.HtmlDiff()
                .make_table(
                    fromlines=rcv_output,
                    tolines=exp_output,
                    fromdesc="Your program's output",
                    todesc="Expected output",
                )
                .replace(colgroup_old, colgroup_new)
            )
            err_diff = (
                difflib.HtmlDiff()
                .make_table(
                    fromlines=rcv_error,
                    tolines=exp_error,
                    fromdesc="Your program's errors",
                    todesc="Expected errors",
                )
                .replace(colgroup_old, colgroup_new)
            )

            diff_tables += out_diff
            diff_tables += err_diff

        if reference:
            exp_outputfiles = reference["outputfiles"]
        elif expected:
            exp_outputfiles = expected["outputfiles"]

        for filename, content in exp_outputfiles.items():
            diff_tables += "<h3>File: %s</h3>\n" % (str(filename.decode("utf-8")))

            exp_content = content.split("\n")
            if filename in test_result["outputfiles"].keys():
                rcv_content = str(test_result["outputfiles"][filename]).split("\n")
            else:
                rcv_content = [str()]

            file_diff = (
                difflib.HtmlDiff()
                .make_table(
                    fromlines=rcv_content,
                    tolines=exp_content,
                    fromdesc="Your program's output",
                    todesc="Expected output",
                )
                .replace(colgroup_old, colgroup_new)
            )
            diff_tables += file_diff

    return diff_tables
