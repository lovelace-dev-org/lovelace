"""
Security measures for automatically running user-submitted code within file
upload, code input and code replace exercise evaluation tasks. 
"""

import os
import signal
import resource

from signal import SIGKILL, SIGSTOP

def drop_privileges():
    """
    Drop all the privileges that can be reasonably dropped. This is to prevent
    the forked process from harming its creator and from accessing any data
    belonging to the evaluation server process exclusively.

    For more information, review:
    - http://man7.org/linux/man-pages/man2/setresuid.2.html
    - https://docs.python.org/3/library/os.html#os.setresuid
    """

    # Drop the real, effective and saved group and user ids
    try:
        os.setresgid(student_gid, student_gid, student_gid)
        os.setresuid(student_uid, student_uid, student_uid)
    except OSError:
        print("Unable to drop privileges to GID: (r:{s_gid}, e:{s_gid}, s:{s_gid}), UID: (r:{s_uid}, e:{s_uid}, s:{s_uid})".
              format(s_gid=student_gid, s_uid=student_uid))

def limit_resources():
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
    # Prevent the scope of fork bombs by limiting the total number of processes
    resource.setrlimit(resource.RLIMIT_NPROC, (10, 10))

    # Prevent filling up memory and file system by limiting the total number of
    # allowed files that the process is allowed to create
    resource.setrlimit(resource.RLIMIT_NOFILE, (50, 50))

    # Prevent filling up memory and disk space by limiting the total number of
    # bytes occupied by one file
    resource.setrlimit(resource.RLIMIT_FSIZE, (500*1024, 500*1024))

    # Prevent arbitrary use of computing power by limiting the amount of CPU time
    # in seconds
    resource.setrlimit(resource.RLIMIT_CPU, (2, 2)) 

def secure_kill(pid):
    """
    Use SIGSTOP and SIGKILL signals to clean up any remaining processes. In
    order to prevent a perpetual fork bomb, a simple SIGKILL is not enough –
    a single SIGKILL will reliably kill _one_ process, which will leave room
    for the other processes to spawn more processes, resulting in a neverending
    SIGKILL whack-a-mole. By using SIGSTOP first to freeze the forking
    processes and KILLing them after that, the fork bomb clean up should be
    more reliable.

    Neither SIGKILL nor SIGSTOP can be captured or blocked by any process.

    NOTE: Requires the issuing process to match its real or effective UID with
          the real or saved UID of the receiving process.[1]

    [1] https://linux.die.net/man/3/kill
    """
    # DEBUG
    user = "student"
    timeout = 5

    kill_age = timeout + 5

    # Iterate through the processes and issue SIGSTOP
    os.system("killall -STOP --verbose --user {user} --younger-than {kill_age}s".format(user=user, kill_age=kill_age))

    # Iterate through the processes again and issue SIGKILL
    os.system("killall -KILL --verbose --user {user} --younger-than {kill_age}s".format(user=user, kill_age=kill_age))
    
