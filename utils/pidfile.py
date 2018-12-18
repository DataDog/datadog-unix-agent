# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
import logging
import os.path
import tempfile

log = logging.getLogger(__name__)


class PidFile(object):
    """ A small helper class for pidfiles. """

    @classmethod
    def get_dir(cls, run_dir=None):
        if run_dir is None:
            my_dir = os.path.dirname(os.path.abspath(__file__))
            run_dir = os.path.realpath(os.path.join(my_dir, '..', '..', 'run'))

        if os.path.exists(run_dir) and os.access(run_dir, os.W_OK):
            return os.path.realpath(run_dir)
        else:
            run_dir = tempfile.gettempdir()
            log.info("Must resort to temporary directory for pidfile: %s" % run_dir)
            return run_dir

    def __init__(self, program, pid_dir=None):
        self.pid_file = "%s.pid" % program
        self.pid_dir = self.get_dir(pid_dir)
        self.pid_path = os.path.join(self.pid_dir, self.pid_file)

    def get_path(self):
        # if all else fails
        if os.access(self.pid_dir, os.W_OK):
            log.info("Pid file is: %s" % self.pid_path)
            return self.pid_path
        else:
            # Can't save pid file, bail out
            log.error("Cannot save pid file: %s" % self.pid_path)
            raise Exception("Cannot save pid file: %s" % self.pid_path)

    def clean(self):
        try:
            path = self.get_path()
            log.debug("Cleaning up pid file %s" % path)
            os.remove(path)
            return True
        except Exception:
            log.warn("Could not clean up pid file")
            return False

    def get_pid(self):
        "Retrieve the actual pid"
        try:
            pf = open(self.get_path())
            pid_s = pf.read()
            pf.close()

            return int(pid_s.strip())
        except Exception:
            return None
