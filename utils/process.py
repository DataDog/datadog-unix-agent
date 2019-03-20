# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import errno
import inspect
import subprocess
import os
import tempfile
import logging
from functools import wraps

try:
    import psutil
except ImportError:
    psutil = None

log = logging.getLogger(__name__)


class SubprocessOutputEmptyError(Exception):
    pass


def pid_exists(pid):
    """
    Check if a pid exists.
    Lighter than psutil.pid_exists
    """
    if psutil:
        return psutil.pid_exists(pid)

    # Code from psutil._psposix.pid_exists
    # See https://github.com/giampaolo/psutil/blob/master/psutil/_psposix.py
    if pid == 0:
        # According to "man 2 kill" PID 0 has a special meaning:
        # it refers to <<every process in the process group of the
        # calling process>> so we don't want to go any further.
        # If we get here it means this UNIX platform *does* have
        # a process with id 0.
        return True
    try:
        os.kill(pid, 0)
    except OSError as err:
        if err.errno == errno.ESRCH:
            # ESRCH == No such process
            return False
        elif err.errno == errno.EPERM:
            # EPERM clearly means there's a process to deny access to
            return True
        else:
            # According to "man 2 kill" possible error values are
            # (EINVAL, EPERM, ESRCH) therefore we should never get
            # here. If we do let's be explicit in considering this
            # an error.
            raise err
    else:
        return True


def is_my_process(pid):
    """
    Check if the pid in the pid given corresponds to a running process
    and if psutil is available, check if it's process corresponding to
    the current executable
    """
    pid_existence = pid_exists(pid)

    if not psutil or not pid_existence:
        return pid_existence

    try:
        command = psutil.Process(pid).cmdline() or []
    except psutil.Error:
        # If we can't communicate with the process,
        # it's not an agent one
        return False
    # Check that the second arg contains (agent|dogstatsd).py
    # see http://stackoverflow.com/a/2345265
    exec_name = os.path.basename(inspect.stack()[-1][1]).lower()
    return len(command) > 1 and exec_name in command[1].lower()


def get_subprocess_output(command, log, raise_on_empty_output=True, env=None,
                          output_as_string=True, sudo=False, timeout=None):
    """
    Run the given subprocess command and return its output. Raise an Exception
    if an error occurs.
    """
    args = command if type(command) == list else [command]
    if sudo:
        args.insert(0, 'sudo')

    stdout, stderr, ret_code = subprocess_output(args, raise_on_empty_output, env, timeout)
    if output_as_string:
        stdout = stdout.decode('utf-8')
        stderr = stderr.decode('utf-8')

    return stdout, stderr, ret_code


def subprocess_output(command, raise_on_empty_output, env, timeout=None):
    """
    Run the given subprocess command and return its output. This is a private method
    and should not be called directly, use `get_subprocess_output` instead.
    """

    # Use tempfile, allowing a larger amount of memory. The subprocess.Popen
    # docs warn that the data read is buffered in memory. They suggest not to
    # use subprocess.PIPE if the data size is large or unlimited.
    with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
        proc = subprocess.Popen(command, env=env, stdout=stdout_f, stderr=stderr_f)
        proc.wait(timeout)
        stderr_f.seek(0)
        err = stderr_f.read()
        stdout_f.seek(0)
        output = stdout_f.read()

    if not output and raise_on_empty_output:
        raise SubprocessOutputEmptyError("get_subprocess_output expected output but had none.")

    return (output, err, proc.returncode)


def log_subprocess(func):
    """
    Wrapper around subprocess to log.debug commands.
    """
    @wraps(func)
    def wrapper(*params, **kwargs):
        fc = "%s(%s)" % (func.__name__, ', '.join(
            [a.__repr__() for a in params] +
            ["%s = %s" % (a, b) for a, b in kwargs.items()]
        ))
        log.debug("%s called" % fc)
        return func(*params, **kwargs)
    return wrapper


subprocess.Popen = log_subprocess(subprocess.Popen)
