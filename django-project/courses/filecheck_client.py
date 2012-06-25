# -*- coding: utf-8 -*-
"""Module for connecting to the file checking bot on a remote machine using JSON-RPC."""

import bjsonrpc

from courses.models import FileTaskTest, FileTaskTestCommand, FileTaskTestExpectedOutput, FileTaskTestExpectedError, FileTaskTestIncludeFile
from courses.models import FileTaskReturnFile

def check_file_answer(answer):
    """Iterates through all the tests for a returnable package of user content."""
    print "Checking a file"

    # Read the returned files from database objects
    ft_returned_files = FileTaskReturnFile.objects.filter(returnable=answer.returnable)
    codefiles = {}
    for ft_returned_file in ft_returned_files:
        with open(ft_returned_file.fileinfo.path, 'r') as f:
            codefiles[ft_returned_file.filename()] = f.read()
            print ft_returned_file.filename()

    # Construct the tests from database objects
    ft_tests = FileTaskTest.objects.filter(task=answer.task)
    tests = []
    references = {}
    for ft_test in ft_tests:
        ft_test_commands = FileTaskTestCommand.objects.filter(test=ft_test)
        commands = [tc.command_line for tc in ft_test_commands]

        ft_test_expected_outputs = FileTaskTestExpectedOutput.objects.filter(test=ft_test)
        outputs = [eo.expected_answer for eo in ft_test_expected_outputs]

        ft_test_expected_errors = FileTaskTestExpectedError.objects.filter(test=ft_test)
        errors = [eo.expected_answer for eo in ft_test_expected_errors]

        ft_test_include_files = FileTaskTestIncludeFile.objects.filter(test=ft_test)
        include_files = {}
        for ft_test_include_file in ft_test_include_files:
            filename = ft_test_include_file.name
            with open(ft_test_include_file.fileinfo.path, 'r') as f:
                include_files[filename] = f.read()
            if ft_test_include_file.purpose == "REFERENCE":
                references[filename] = include_files[filename]

        test = {"args": commands,
                "input": [ft_test.inputs],
                "inputfiles": {},
                "output": outputs,
                "outputfiles": {},
               }
        tests.append(test)

    # test code
    #test1 = {"args": ['python *.py'],
    #         "input": [],
    #         "inputfiles": {},
    #        }
    #codes = {"lolol.py": "print 'hello, world'"}
    #references = {"hello.py": "print 'Hello, world!'"}
    #tests = [test1]

    print tests

    results = None

    bjsonrpc_client = bjsonrpc.connect(host='127.0.0.1', port=10123)
    if references:
        results = bjsonrpc_client.call.checkWithReference(codefiles, references, tests)
        print results
        results = {"output": results[0][0]["output"], "ref_output":results[1][0]["output"]}
    elif outputs:
        results = bjsonrpc_client.call.checkWithOutput(codefiles, tests)
        print results
        results = {"output": results[0]["output"], "ref_output":test["output"][0]}
    
    print "File checked"

    return results
