# checks/corechecks/system/load/load.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.

import os
import psutil

from utils.process import get_subprocess_output
from checks import AgentCheck


class LoadCheck(AgentCheck):
    """
    Core system load check with AIX fallback behavior.
    """

    __slots__ = tuple()

    def check(self, instance):
        try:
            load = os.getloadavg()
        except AttributeError:
            # AIX fallback: parse load averages from uptime output
            out, _, _ = get_subprocess_output(["uptime"], self.log)
            fields = out.strip().split(" ")
            load = [
                float(fields[-3].strip(",")),
                float(fields[-2].strip(",")),
                float(fields[-1].strip(",")),
            ]

        self.gauge("system.load.1", load[0])
        self.gauge("system.load.5", load[1])
        self.gauge("system.load.15", load[2])

        cores = psutil.cpu_count()
        assert cores >= 1, "Cannot determine number of cores"

        self.gauge("system.load.norm.1", load[0] / cores)
        self.gauge("system.load.norm.5", load[1] / cores)
        self.gauge("system.load.norm.15", load[2] / cores)
