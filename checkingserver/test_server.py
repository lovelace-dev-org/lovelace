# -*- coding: utf-8 -*-
"""
@copyright: 2008 by Mika Seppänen, Rauli Puuperä, Erno Kuusela
@license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

import datetime
import time
import socket
import json
import os
import shlex
import subprocess
import tempfile
import shutil
import difflib

import bjsonrpc
from bjsonrpc.handlers import BaseHandler

def error(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [error] %s" % (date, msg)

def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s [info] %s" % (date, msg)

def demote():
    pass

def runTest(arg, input, tempdir, timeout=10):

    #open files for stdout and stderr
    outpath = os.path.join(tempdir, '__out__')
    errpath = os.path.join(tempdir, '__err__')
    inpath = os.path.join(tempdir, '__in__')
    
    outfile = open(outpath, "w")
    errfile = open(errpath, "w")
    
    open(inpath, 'w').write("\n".join(input))
    infile = open(inpath, 'r')

    # http://stackoverflow.com/a/6037494
    # TODO: Many security measures!
    # Running external code is _dangerous_! Therefore, we must do our best to prevent the following:
    # 1. Code uses too many resources (memory, cpu, takes too much time to run etc.)
    # -> use ulimit?
    # 2. Code tries to access/delete files/directories on the machine
    # -> set proper chmods for all files, run the code with a low privileged user
    # 3. Code tries to send a KILL signal to a process (e.g. this checking bot)
    # -> run the code with a different user than this checking bot
    # use grsecurity?

    #if arg:
    #    arg = shlex.split(arg)
    #p = subprocess.Popen('ulimit -f 50 -n 50;' + arg, shell=True, stdout=outfile, stderr=errfile, stdin=infile)
    p = subprocess.Popen(
        args='ulimit -f 50 -n 50;' + arg,
        #preexec_fn=demote(),
        shell=True,
        cwd=tempdir,
        universal_newlines=True,
        stdout=outfile,
        stderr=errfile,
        stdin=infile
    )
    
    timedout = True
    counter = 0
    while counter < timeout:
        if p.poll() is not None:
            timedout = False
            break
        time.sleep(0.2)
        counter += 0.2
    
    # if timeout then kill
    if timedout:
        info('Timed out!')
        os.kill(p.pid, signal.SIGTERM)
        time.sleep(2)
        p.poll()
        try:
            os.kill(p.pid, signal.SIGKILL)
        except OSError:
            info('Killed by SIGTERM')
        else:
            info('Killed by SIGKILL')
        
    outfile.close()
    errfile.close()
    
    error = open(errpath).read()
    output = open(outpath).read()
    
    #clean files
    os.remove(outpath)
    os.remove(errpath)
    os.remove(inpath)

    outfiles = dict()

    for ofile in os.listdir(tempdir):
        outfiles[ofile] = open(ofile).read()

    return output, outfiles, error, timedout

def runTests(codes, tests, tempdir):

    for filename, content in codes.items():
        info('Writing sourcefile %s' % filename)
        open(os.path.join(tempdir, filename), 'w').write(content)

    testResults = list()

    for test in tests:
        result = dict()
        
        error = str()
        output = str()
        outfiles = dict()

        args = test['args']
        input = test['input']
        inputfiles = test['inputfiles']

        timedout = False
        for arg in args:
            routput, ofiles, rerror, rtimedout = runTest(arg, input, tempdir)
            error += rerror
            output += routput
            for k, v in ofiles.items():
                if k not in codes and k not in inputfiles:
                    outfiles[k] = v
            timedout = timedout or rtimedout

        result['output'] = output
        result['error'] = error
        result['outputfiles'] = outfiles
        result['timedout'] = timedout

        testResults.append(result)
        
        for filename in os.listdir(tempdir):
            #clean up everything except the codes
            if filename not in codes:
                os.remove(os.path.join(tempdir, filename))

    return testResults


def maketemp():
    #tempdir = "/Users/therauli/src/newRaippa/temp" #tempfile.mkdtemp()
    tempdir = "/home/mdf/temp/raippa_temp"
    info("Created tempdir %s" % tempdir)
    os.chdir(tempdir)
    return tempdir

class ConnectionHandler(BaseHandler):

    def test(self, test):
        print "Test", test
        return "Test", test

    def checkWithReference(self, codes, references, tests):
        tempdir = maketemp()

        print repr(codes)
        print repr(references)
        print repr(tests)

        referenceResults = runTests(references, tests, tempdir)
        print referenceResults
        studentResults = runTests(codes, tests, tempdir)

        #compare output
        for i in range(len(tests)):
            print studentResults[i], referenceResults[i]
                       
        info('Removing ' + tempdir)
        #shutil.rmtree(tempdir) #fixme

        return studentResults, referenceResults

    def checkWithOutput(self, codes, tests):
        tempdir = maketemp()

        print repr(codes)
        print repr(tests)

        studentResults = runTests(codes, tests, tempdir)
        print studentResults

        #compare with output
        for i, test in enumerate(tests):
            print test["output"], studentResults[i]['output']

        info('Removing ' + tempdir)
        #shutil.rmtree(tempdir) #fixme
        return studentResults

test1 = {"args": ['python *.py'],
        "input": [],
        "inputfiles" : {},
        "output": [],
        "outputfiles": {},
        }

testCases = {"codes": {"foo.py": "print 'hello World'"},
             "references": {"hello.py": "print 'Hello World!'"},
             "tests": [test1],
             }


# Lataa testit ja koodit
# aja testi referenssi toteutuksella
# aja opiskelijan koodilla
# vertaa output + stderr
# vertaa muodostetut tiedostot

# c = ConnectionHandler(None)
# test1 = {"args": ['python *.py'],
# "input": [],
# "inputfiles" : {},
# }
# codes = {"foo.py": "print 'hello World'"}
# references = {"hello.py": "print 'Hello World!'"}
# tests = [test1]
# c.checkWithReference(codes, references, tests)

server = bjsonrpc.createserver(host='127.0.0.1', port=10123, handler_factory=ConnectionHandler)
server.debug_socket(True)
server.serve()
