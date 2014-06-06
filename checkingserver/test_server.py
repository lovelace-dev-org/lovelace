# -*- coding: utf-8 -*-
"""
@copyright: 2008 by Mika Seppänen, Rauli Puuperä, Erno Kuusela, 2012 by Rauli Puuperä, Miikka Salminen
@license: MIT <http://www.opensource.org/licenses/mit-license.php>
"""

# FUTURE: Use LD_PRELOAD?
# TODO: Rewrite from scratch, using rabbitmq (and celery?)
#       - Multiple task processors running at the same time
#         * Can serve multiple users returning code simultaneously
#         * Can do multiple tests per file task simultaneously
#       - Check some ready made containers LXC etc. 

import os
import re
import pwd
import datetime
import time
import fcntl
import shlex
import pipes
import codecs
import resource
import subprocess
import tempfile
import shutil
import sys
import base64

from signal import SIGINT, SIGTERM, SIGKILL

sys.path.append("/var/local/raippa/dependencies/")
import bjsonrpc
from bjsonrpc.handlers import BaseHandler

class colors:
    _CSI = "\x1B["
    reset = _CSI+"m"
    fgred = _CSI+"31m"
    fgcyan = _CSI+"36m"
    fgyellow = _CSI+"33m"

def error(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s %s[error]%s %s" % (date, colors.fgred, colors.reset, msg)

def info(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s %s[info]%s %s" % (date, colors.fgcyan, colors.reset, msg)

def note(msg):
    date = datetime.datetime.now().isoformat()[:19]
    print "%s %s[note]%s %s" % (date, colors.fgyellow, colors.reset, msg)

def runCommand(arg, input_data, tempdir, outfile, errfile, infile, signal=None, timeout=10):
    """Run one command from a test."""
    env = {'HOME':tempdir, 'LOGNAME':Privileges.get_low_name(), 'PWD':tempdir, 'USER':Privileges.get_low_name(),
           'PATH':'/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin',
           'PYTHONPATH':''}
    info("Running command: %s" % (" ".join((pipes.quote(s) for s in arg))))

    p = subprocess.Popen(
        args=arg,
        executable=arg[0],
        preexec_fn=demote_subprocess,
        cwd=tempdir,
        env=env,
        universal_newlines=False,
        stdout=outfile,
        stderr=errfile,
        stdin=infile
        )

    act("server") # Is this soon enough to prevent the child from killing the parent?

    if signal:
        time.sleep(0.5)
        if signal == "SIGINT":
            os.kill(p.pid, SIGINT)
    
    timedout = True
    counter = 0
    while counter < timeout:
        retval = p.poll()
        if retval is not None:
            timedout = False
            info("Subprocess died with return value %d." % (retval))
            break
        time.sleep(0.2)
        counter += 0.2
    
    act("subprocess")
    # Kill the subprocess if it times out
    if timedout:
        info('Child timed out! Terminating.')
        p.terminate()
        time.sleep(0.1)
        p.poll()
        try:
            p.kill()
        except OSError:
            info('Child killed with SIGTERM.')
        else:
            info('Child killed with SIGKILL.')

    # Clean up in case there was a fork bomb
    #act("server")
    #os.system("killall -9 -v -g -u %s" % (Privileges.get_low_name()))
    # TODO: FIX FOR CENTOS!
    #os.system("killall -STOP --verbose --user %s --younger-than %ds" % (Privileges.get_low_name(), timeout + 5))
    #os.system("killall -9 --verbose --user %s --younger-than %ds" % (Privileges.get_low_name(), timeout + 5))
    #act("subprocess")

    return retval, timedout

def build_arg(arg, returnables):
    #re_arg =
    #re.match(r"\$returnables(\((?P<old>.+)\,\s+(?P<new>.+)\))?", arg)
    new_args = shlex.split(arg)
    new_args2 = []
    for new_arg in new_args[::]:
        if new_arg == "$returnables":
            new_args2.extend(returnables)
        else:
            new_args2.append(new_arg)

    #return arg.replace("$returnables", " ".join(returnables))
    return new_args2

def runTest(args, input_data, input_files, code_files, signal, tempdir, timeout=10):
    """
    Runs all the commands of one test.
    Enters the specified inputs.
    Saves the stdout, stderr and contents of created files.
    """
    outpath = os.path.join(tempdir, '__out__')
    errpath = os.path.join(tempdir, '__err__')
    inpath = os.path.join(tempdir, '__in__')

    timedout = False
    outputs = []
    errors = []
    rvalues = []
    outfiles = {}
    for arg, is_main_arg in args:
        # Fill the stdin file with the specified input
        with codecs.open(inpath, "w", "utf-8") as infile_w:
            # Only enter the input for the main command (i.e., usually, the interpreted or compiled program)
            if is_main_arg:
                infile_w.write(input_data.replace("\r\n", "\n"))
        # Open files for stdout, stderr and stdin and run the current command
        # TODO: Consider a separate temporary path for stdout, stderr and stdin files or use temporary files instead
        outfile = codecs.open(outpath, "w", "utf-8")
        errfile = codecs.open(errpath, "w", "utf-8")
        infile = codecs.open(inpath, "r", "utf-8")

        rvalue, rtimedout = runCommand(arg, input_data, tempdir, outfile, errfile, infile, signal, timeout)
        timedout = timedout or rtimedout
        rvalues.append(rvalue)
        
        outfile.close()
        errfile.close()
        infile.close()

        # Save the contents of stdout and stderr
        with open(outpath, "rb") as outfile_r:
            outputs.append(outfile_r.read())
        with open(errpath, "rb") as errfile_r:
            errors.append(errfile_r.read())

        # Clean up the files
        os.remove(outpath)
        os.remove(errpath)
        os.remove(inpath)

        # Save the contents of files created by running the commands
        for ofile in os.listdir(tempdir):
            if ofile not in code_files and ofile not in input_files:
                with open(ofile, "rb") as f:
                    outfiles[ofile] = f.read()

    return outputs, outfiles, errors, rvalues, timedout

def maketemp():
    tempdir = tempfile.mkdtemp()
    os.chdir(tempdir)
    info("Created temporary directory '%s'. For debug:  sudo ls -la %s  and  sudo cat %s/__err__ " % (tempdir, tempdir, tempdir))
    return tempdir

def runTests(code_files, tests):
    """
    Runs all the tests for the given codes.
    """
    tempdir = maketemp()

    testResults = {}
    for test in tests:
        testname = test['name']
        args = [(build_arg(newarg, code_files), is_main) for newarg, is_main in test['args']]
        unittests = {k: base64.b64decode(v) for k, v in test['unittests'].iteritems()}
        inputgens = {k: base64.b64decode(v) for k, v in test['inputgens'].iteritems()}
        input_data = test['input']
        input_files = {k: base64.b64decode(v) for k, v in test['inputfiles'].iteritems()}
        output_files = test['outputfiles']
        signal = test['signal']
        timeout = test['timeout']

        # Write the submitted codes and input files
        for filename, content in code_files.iteritems():
            info('Writing source file %s' % filename)
            if type(content) == type(unicode()):
                # It's a reference file, assumme utf-8
                with codecs.open(os.path.join(tempdir, filename), 'w', 'utf-8') as source_file:
                    source_file.write(content)
            else: 
                # It's a binary blob sent by a student
                with open(os.path.join(tempdir, filename), 'wb') as source_file:
                    source_file.write(content)
        for filename, content in input_files.iteritems():
            info('Writing input file %s' % filename)
            with open(os.path.join(tempdir, filename), 'wb') as input_file:
                input_file.write(content)
        for filename, content in unittests.iteritems():
            info('Writing unit test file %s' % filename)
            with open(os.path.join(tempdir, filename), 'wb') as unittest:
                unittest.write(content)

        # TODO: Generate stdin and file inputs with INPUTGEN if it exists
        # - anything INPUTGEN gives as stdout will be used as stdin (input_data)
        # - any files INPUTGEN writes shall be used input files (input_files)
        # test['inputgens']

        routputs, routfiles, rerrors, rvalues, rtimedout = runTest(args, input_data, input_files, code_files, signal, tempdir, timeout)

        result = {}
        result['cmds'] = args
        result['outputs'] = routputs
        result['errors'] = rerrors
        result['unittests'] = {k: base64.b64encode(v) for k, v in unittests.iteritems()}
        result['input'] = input_data
        result['inputfiles'] = {k: base64.b64encode(v) for k, v in input_files.iteritems()}
        result['inputgens'] = {k: base64.b64encode(v) for k, v in inputgens.iteritems()}
        result['outputfiles'] = {k: v for k, v in routfiles.iteritems() if k in output_files}
        result['returnvalues'] = rvalues
        result['timedout'] = rtimedout
        testResults[testname] = result

        # Clean up everything from the temporary directory
        for filename in os.listdir(tempdir):
            if filename not in code_files:
                os.remove(os.path.join(tempdir, filename))

    info('Removing ' + tempdir)
    shutil.rmtree(tempdir)

    return testResults

class ConnectionHandler(BaseHandler):

    def test(self, test):
        print "Test", test
        return "Test", test

    def checkWithReference(self, codes, references, tests):
        """Run the same tests for both the students' files and the reference implementation."""
        note("Received a test set with codes and reference codes.")

        # Base 64 decode the binary blobs students call source code
        for name, contents in codes.iteritems():
            codes[name] = base64.b64decode(contents)

        for name, contents in references.iteritems():
            references[name] = base64.b64decode(contents)

        # Get the results by running the tests and base 64 encode them
        # for transmission back to the web application
        referenceResults = runTests(references, tests)
        for test_name, test_result in referenceResults.iteritems():
            test_result["outputs"] = [base64.b64encode(output) for output in test_result["outputs"]]
            test_result["errors"] = [base64.b64encode(error) for error in test_result["errors"]]
            for output_file_name, output_file_contents in test_result["outputfiles"].iteritems():
                test_result["outputfiles"][output_file_name] = base64.b64encode(output_file_contents)

        studentResults = runTests(codes, tests)
        for test_name, test_result in studentResults.iteritems():
            test_result["outputs"] = [base64.b64encode(output) for output in test_result["outputs"]]
            test_result["errors"] = [base64.b64encode(error) for error in test_result["errors"]]
            for output_file_name, output_file_contents in test_result["outputfiles"].iteritems():
                test_result["outputfiles"][output_file_name] = base64.b64encode(output_file_contents)

        info("Testing successful. Returning results.")
        return {"student":studentResults, "reference":referenceResults}

    def checkWithOutput(self, codes, tests):
        """Run the tests for the students' files only."""
        note("Received a test set with codes.")

        # Base 64 decode the binary blobs students call source code
        for name, contents in codes.iteritems():
            codes[name] = base64.b64decode(contents)

        # Get the results by running the tests and base 64 encode them
        # for transmission back to the web application
        studentResults = runTests(codes, tests)
        for test_name, test_result in studentResults.iteritems():
            test_result["outputs"] = [base64.b64encode(output) for output in test_result["outputs"]]
            test_result["errors"] = [base64.b64encode(error) for error in test_result["errors"]]
            for output_file_name, output_file_contents in test_result["outputfiles"].iteritems():
                test_result["outputfiles"][output_file_name] = base64.b64encode(output_file_contents)
        
        info("Testing successful. Returning results.")
        return {"student":studentResults}

class Privileges:
    _low = {"username":"", "userid":0, "groupid":0}
    _high = {"username":"", "userid":0, "groupid":0}

    @staticmethod
    def set_info(todict, name, uid, gid):
        todict["username"] = name
        todict["userid"] = uid
        todict["groupid"] = gid

    @staticmethod
    def set_low(name, uid, gid):
        Privileges.set_info(Privileges._low, name, uid, gid)
    
    @staticmethod
    def set_high(name, uid, gid):
        Privileges.set_info(Privileges._high, name, uid, gid)

    @staticmethod
    def get_low_gid():
        return Privileges._low["groupid"]

    @staticmethod
    def get_high_gid():
        return Privileges._high["groupid"]

    @staticmethod
    def get_low_uid():
        return Privileges._low["userid"]

    @staticmethod
    def get_high_uid():
        return Privileges._high["userid"]

    @staticmethod
    def get_low_name():
        return Privileges._low["username"]

    @staticmethod
    def get_high_name():
        return Privileges._high["username"]

def act(act_as):
    srv_uid = Privileges.get_high_uid()
    srv_gid = Privileges.get_high_gid()
    sp_uid = Privileges.get_low_uid()
    sp_gid = Privileges.get_low_gid()
    try:
        if act_as == "server":
            os.setresgid(srv_gid, sp_gid, srv_gid)
            os.setresuid(srv_uid, sp_uid, srv_uid)
        elif act_as == "subprocess":
            os.setresgid(srv_gid, sp_gid, sp_gid)
            os.setresuid(srv_uid, sp_uid, sp_uid)
    except OSError:
        error("Unable to set effective user rights as %s!" % (act_as))
    else:
        info("Effective user: %s." % (act_as))

def get_uid_gid(username):
    pwrec = pwd.getpwnam(username)
    uid = pwrec.pw_uid
    gid = pwrec.pw_gid
    return (uid, gid)

def demote_server():
    srv_uid = Privileges.get_high_uid()
    srv_gid = Privileges.get_high_gid()
    srv_name = Privileges.get_high_name()
    sp_uid = Privileges.get_low_uid()
    sp_gid = Privileges.get_low_gid()

    # Demote the server to server_uid, but allow further demotion to sp_uid
    try:
        # http://stackoverflow.com/a/6037494
        os.setresgid(srv_gid, sp_gid, sp_gid)
        os.setresuid(srv_uid, sp_uid, sp_uid)
    except OSError:
        error("Losing privileges not permitted.")
    else:
        info("Demoted the server process to user %s (%d) and group %d." % (srv_name, srv_uid, srv_gid))

def demote_subprocess():
    """
    Lower the privileges of the spawned subprocess by setting limits on its resource use and
    by switching it to be run as another user.

    NOTE: The resource limits were set by using ulimit and shell=True before. This was changed
          in order to address security questions raised by using the shell and to make passing
          arguments easier.
    """
    #info("Demoting subprocess.")
    # Set resource limits
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))  # Prevent fork bombs
    resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50)) # Limit number of files
    resource.setrlimit(resource.RLIMIT_FSIZE, (500*1024, 500*1024))  # Limit space used by a file
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2))      # Limit CPU time
    
    # Change the group and user IDs to lower privileged ones
    user_gid = Privileges.get_low_gid()
    user_uid = Privileges.get_low_uid()
    try:
        os.setresgid(user_gid, user_gid, user_gid)
        os.setresuid(user_uid, user_uid, user_uid)
    except OSError:
        #error("Unable to demote the subprocess to uid: %d, gid: %d!" % (user_uid, user_gid))
        pass
    else:
        #info("Successfully demoted the subprocess to uid: %d, gid: %d." % (user_uid, user_gid))
        pass

def start():
    '''
    Starts the process as a daemon.
    http://daemonize.sourceforge.net/daemonize.txt used as an example.
    '''

    # Fork a child and quit the parent
    pid = os.fork()
    if pid < 0:
        sys.exit(1)
    elif pid != 0:
        sys.exit(0)

    # Get a new PID and detach from terminal
    pid = os.setsid()
    if pid == -1:
        sys.exit(1)

    # Set the file descriptors to null
    if hasattr(os, "devnull"):
        dev_null = os.devnull
    else:
        dev_null = "/dev/null"
    null_fd = open(dev_null, "rw")
    log_fd = open("/tmp/test_server.log", "w", 0)
    for fd in (sys.stdin, sys.stdout, sys.stderr):
        fd.close()

    sys.stdin = null_fd
    sys.stdout = log_fd
    sys.stderr = log_fd

    os.umask(027) # Set default file creation mask
    os.chdir("/")
    lock_fd = open("/tmp/test_server.lock", "w")
    fcntl.lockf(lock_fd, fcntl.LOCK_EX|fcntl.LOCK_NB)
    lock_fd.write("%s" % (os.getpid()))
    lock_fd.flush()

    main()

def main():
    server_username = "program_evaluator"
    subprocess_username = "test_subject"
    host = "0.0.0.0"
    port = 10123

    srv_uid, srv_gid = get_uid_gid(server_username)
    sp_uid, sp_gid = get_uid_gid(subprocess_username)

    Privileges.set_low(subprocess_username, sp_uid, sp_gid)
    Privileges.set_high(server_username, srv_uid, srv_gid)

    uid = os.getuid()
    if uid == 0:
        info("Running as a root. Trying to lose privileges.")
        demote_server()
    else:
        info("Running as a normal user. Warning! Dangerous code will have the same rights as the server, enabling a malicious user to kill the server!")
    
    # Run the server
    server = bjsonrpc.createserver(host=host, port=port, handler_factory=ConnectionHandler)
    server.debug_socket(False)
    for i in range(10):
        if 0 == os.fork():
            server.serve()
            os._exit(0)
    os.waitpid(-1, 0)

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "--daemon":
            start()
        elif sys.argv[1] == "--die":
            lock_fd = open("/tmp/test_server.lock", "r")
            os.kill(int(lock_fd.read().strip()), SIGTERM)
            lock_fd.close()
            os.remove("/tmp/test_server.lock") # TODO: Use os.path.join
            sys.exit(0)
        else:
            main()
    else:
        main()
