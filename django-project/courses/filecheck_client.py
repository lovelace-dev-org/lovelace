# -*- coding: utf-8 -*-
"""
Module for connecting to the file checking bot on a remote machine using JSON-RPC and generating HTML
from the test results.
"""

import bjsonrpc
import difflib
import datetime

from courses.models import FileTaskTest, FileTaskTestCommand, FileTaskTestExpectedOutput, FileTaskTestExpectedError, FileTaskTestIncludeFile
from courses.models import FileTaskReturnFile

def check_file_answer(task, files={}, answer=None):
    """Iterates through all the tests for a returnable package of user content."""
    print "Checking a file"
    _secs = lambda dt: dt.hour*3600+dt.minute*60+dt.second

    # Read the returned files from database objects
    if answer:
        ft_returned_files = FileTaskReturnFile.objects.filter(returnable=answer.returnable)
        codefiles = {}
        for ft_returned_file in ft_returned_files:
            with open(ft_returned_file.fileinfo.path, 'r') as f:
                codefiles[ft_returned_file.filename()] = f.read()
                print ft_returned_file.filename()
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
        commands = [(tc.command_line, tc.main_command) for tc in ft_test_commands] or ['']

        ft_test_expected_outputs = FileTaskTestExpectedOutput.objects.filter(test=ft_test)
        outputs = [eo.expected_answer for eo in ft_test_expected_outputs] or ['']

        ft_test_expected_errors = FileTaskTestExpectedError.objects.filter(test=ft_test)
        errors = [ee.expected_answer for ee in ft_test_expected_errors] or ['']

        ft_test_include_files = FileTaskTestIncludeFile.objects.filter(test=ft_test)
        include_files = {}
        input_files = {}
        output_files = {}
        for ft_test_include_file in ft_test_include_files:
            filename = ft_test_include_file.name
            with open(ft_test_include_file.fileinfo.path, 'r') as f:
                include_files[filename] = f.read()
            if ft_test_include_file.purpose == "REFERENCE":
                references[filename] = include_files[filename]
            elif ft_test_include_file.purpose == "INPUT":
                input_files[filename] = include_files[filename]
            elif ft_test_include_file.purpose == "OUTPUT":
                output_files[filename] = include_files[filename]

        test = {"name": ft_test_name,
                "timeout": _secs(ft_test_timeout),
                "signal": ft_test_signal,
                "args": commands,
                "input": ft_test_input,
                "inputfiles": input_files,
                "output": outputs,
                "outputfiles": output_files,
                "errors": errors,
               }
        tests.append(test)
        expected[ft_test_name] = {"outputs":outputs, "outputfiles":output_files, "errors":errors}

    print tests

    results = None

    # Send the tests and files to the checking server
    bjsonrpc_client = bjsonrpc.connect(host='10.0.0.10', port=10123)
    if references:
        results = bjsonrpc_client.call.checkWithReference(codefiles, references, tests)
    else:
        results = bjsonrpc_client.call.checkWithOutput(codefiles, tests)
        results["expected"] = expected
    
    print "File checked"

    return results

def html(results):
    diff_tables = "<h1>Test results</h1>"
    expected = None
    reference = None
    for test_name, test_result in results["student"].iteritems():
        # TODO: Use templates instead!
        diff_tables += "<h2>Test: %s</h2>" % (test_name)
        if "reference" in results.keys():
            reference = results["reference"][test_name]
        elif "expected" in results.keys():
            expected = results["expected"][test_name]

        for i, cmd in enumerate(test_result["cmds"]):
            diff_tables += "<h3>Command: %s</h3>" % (cmd[0])

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
                    exp_output = expected["outputs"][0].split("\n")
                    exp_error = expected["errors"][0].split("\n")
                else:
                    exp_retval = 0
                    exp_output = [str()]
                    exp_error = [str()]

            out_diff = difflib.HtmlDiff().make_table(fromlines=rcv_output,tolines=exp_output,fromdesc="Your program's output",todesc="Expected output")
            err_diff = difflib.HtmlDiff().make_table(fromlines=rcv_error,tolines=exp_error,fromdesc="Your program's errors",todesc="Expected errors")

            diff_tables += out_diff
            diff_tables += err_diff

        for filename, content in test_result["outputfiles"].iteritems():
            diff_tables += "<h3>File: %s</h3>" % (filename)

            rcv_content = content.split("\n")

            if reference:
                exp_content = reference["outputfiles"][filename].split("\n")
            elif expected:
                exp_content = expected["outputfiles"][filename].split("\n")

            file_diff = difflib.HtmlDiff().make_table(fromlines=rcv_content,tolines=exp_content,fromdesc="Your program's output",todesc="Expected output")
            diff_tables += file_diff

    return diff_tables
