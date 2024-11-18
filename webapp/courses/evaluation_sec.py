"""
Security measures for automatically running user-submitted code within file
upload, code input and code replace exercise evaluation tasks. Provides
functions for, e.g., sandboxing the user-submitted code to lower privileges
and limiting the OS resources available to the processes to provide a reasonably
safe environment to run unsafe code in.
"""

import logging
import os
import pwd
import resource
import signal
import subprocess

from django.conf import settings

_CONCURRENT_PROCESSES = 40
_NUMBER_OF_FILES = 100
_FILE_SIZE = 4 * (1024**2)  # 4 MiB
_CPU_TIME = 20
_MEMORY_SIZE = 100 * (1024 ** 2) # 100 MiB


logger = logging.getLogger(__name__)

def get_uid_gid(username):
    pwrec = pwd.getpwnam(username)
    uid = pwrec.pw_uid
    gid = pwrec.pw_gid
    return uid, gid


def get_demote_process_fun(
    concurrent_processes=_CONCURRENT_PROCESSES,
    number_of_files=_NUMBER_OF_FILES,
    file_size=_FILE_SIZE,
    cpu_time=_CPU_TIME,
):
    """
    Creates and returns a function that demotes the process based on given
    arguments. Allows setting of custom limits based on, e.g., database values.
    """

    def demote_process():
        """
        Execute a number of security measures to limit the possible scope of harm
        available for the spawned processes to exploit.
        """
        # close_fds()
        drop_privileges()
        limit_resources(
            concurrent_processes=concurrent_processes,
            number_of_files=number_of_files,
            file_size=file_size,
            cpu_time=cpu_time,
        )

    return demote_process


default_demote_process = get_demote_process_fun()


def close_fds():
    """
    Close all file descriptors (i.e. files, sockets etc.) except the standard
    input, output and error streams to ensure that the forked process doesn't
    have access to data it shouldn't have.
    """


def drop_privileges():
    """
    Drop all the privileges that can be reasonably dropped. This is to prevent
    the forked process from harming its creator and from accessing any data
    belonging to the evaluation server process exclusively.

    For more information, review:
    - http://man7.org/linux/man-pages/man2/setresuid.2.html
    - https://docs.python.org/3/library/os.html#os.setresuid
    """

    student_uid, student_gid = get_uid_gid(settings.RESTRICTED_USERNAME)

    # Drop the real, effective and saved group and user ids
    try:
        os.setresgid(student_gid, student_gid, student_gid)
        os.setresuid(student_uid, student_uid, student_uid)
    except OSError:
        logger.error(
            "Unable to drop privileges to "
            "GID: (r:{s_gid}, e:{s_gid}, s:{s_gid}), "
            "UID: (r:{s_uid}, e:{s_uid}, s:{s_uid})".format(s_gid=student_gid, s_uid=student_uid)
        )
    else:
        logger.debug(
            "Dropped privileges to "
            "GID: (r:{s_gid}, e:{s_gid}, s:{s_gid}), "
            "UID: (r:{s_uid}, e:{s_uid}, s:{s_uid})".format(s_gid=student_gid, s_uid=student_uid)
        )

def limit_resources(
    concurrent_processes=_CONCURRENT_PROCESSES,
    number_of_files=_NUMBER_OF_FILES,
    file_size=_FILE_SIZE,
    cpu_time=_CPU_TIME,
    memory=_MEMORY_SIZE,
):
    """
    Use resource.setrlimit to define soft and hard limits for different
    resources available to the forked process.

    For more information, review:
    - https://www.freebsd.org/cgi/man.cgi?query=setrlimit
    - https://linux.die.net/man/2/setrlimit
    - https://docs.python.org/3/library/resource.html#resource.setrlimit

    (For historical context: the early RAiPPA system used the bash command
    ulimit to achieve the same result. However, this command had to be included
    before the command line used to run the student program, by appending the
    actual command line after the ulimit and a semicolon. This also required
    spawning the process with the insecure shell=True setting.)
    """
    # Prevent the scope of fork bombs by limiting the total number of concurrent
    # processes
    resource.setrlimit(resource.RLIMIT_NPROC, (concurrent_processes, concurrent_processes))

    # Prevent filling up memory and file system by limiting the total number of
    # allowed files that the process is allowed to create
    resource.setrlimit(resource.RLIMIT_NOFILE, (number_of_files, number_of_files))

    # Prevent filling up memory and disk space by limiting the total number of
    # bytes occupied by one file
    resource.setrlimit(resource.RLIMIT_FSIZE, (file_size, file_size))

    # Prevent arbitrary use of computing power by limiting the amount of CPU time
    # in seconds
    resource.setrlimit(resource.RLIMIT_CPU, (cpu_time, cpu_time))

    # Prevent filling up memory by limiting heap size
    resource.setrlimit(resource.RLIMIT_DATA, (memory, memory))


def chmod_child_files(test_dir):
    """
    Makes sure everything created during the checking can be removed by the parent process
    when it's cleaning up the temporary directory. Achieved by running chmod as the child.
    """

    proc = subprocess.run(
        ("chmod", "-R", "a+rw", "."),
        bufsize=-1,
        executable=None,
        timeout=5,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        preexec_fn=default_demote_process,  # Demote before fork
        start_new_session=True,
        close_fds=True,  # Don't inherit fds
        shell=False,  # Don't run in shell
        cwd=test_dir,
    )


def secure_kill(pid):
    """
    Use SIGSTOP and SIGKILL signals to clean up any remaining processes. In
    order to prevent a perpetual fork bomb, a simple SIGKILL is not enough –
    a single SIGKILL will reliably kill _one_ process, which will leave room
    for the other processes to spawn more processes (up to the limit defined
    in the limit_resources function), resulting in a neverending SIGKILL
    whack-a-mole. By using SIGSTOP first to freeze the forking processes and
    KILLing them after that, the fork bomb clean up should be more reliable.

    The 'killall' command alone doesn't solve the problem, since the operation
    of killing all the processes is not atomic, i.e., single processes are
    signalled one by one by iterating over a list of them.

    Neither SIGKILL nor SIGSTOP can be captured or blocked by any process.

    [1] https://linux.die.net/man/3/kill
    """
    commands = [
        ("pkill", "--signal", "SIGSTOP", "-s", str(pid)),
        ("pkill", "--signal", "SIGKILL", "-s", str(pid)),
    ]
    for command in commands:
        try:
            proc = subprocess.run(
                command,
                bufsize=-1,
                executable=None,
                timeout=5,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                preexec_fn=default_demote_process,  # Demote before fork
                start_new_session=True,
                close_fds=True,  # Don't inherit fds
                shell=False,  # Don't run in shell
            )
        except subprocess.TimeoutExpired:
            command_str = " ".join(command)
            logger.error(f"Command '{command_str}' timed out")
