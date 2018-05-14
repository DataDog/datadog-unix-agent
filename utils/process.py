# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import subprocess
import tempfile
import logging
from functools import wraps

log = logging.getLogger(__name__)


class SubprocessOutputEmptyError(Exception):
    pass


def get_subprocess_output(command, log, raise_on_empty_output=True, env=None):
    """
    Run the given subprocess command and return its output. Raise an Exception
    if an error occurs.
    """
    return subprocess_output(command, raise_on_empty_output, env)


def subprocess_output(command, raise_on_empty_output, env):
    """
    Run the given subprocess command and return its output. This is a private method
    and should not be called directly, use `get_subprocess_output` instead.
    """

    # Use tempfile, allowing a larger amount of memory. The subprocess.Popen
    # docs warn that the data read is buffered in memory. They suggest not to
    # use subprocess.PIPE if the data size is large or unlimited.
    with tempfile.TemporaryFile() as stdout_f, tempfile.TemporaryFile() as stderr_f:
        proc = subprocess.Popen(command, env=env, stdout=stdout_f, stderr=stderr_f)
        proc.wait()
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
