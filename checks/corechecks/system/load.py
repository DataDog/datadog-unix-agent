# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.
from __future__ import division

import os
import psutil

from utils.process import get_subprocess_output
from checks import AgentCheck


class Load(AgentCheck):

    def check(self, instance):
        try:
            load = os.getloadavg()  # os.getloadvg() not available on AIX fallback to uptime report
        except AttributeError:
            # sample output: '10:50AM   up 8 days,   2:48,  2 users,  load average: 1.19, 0.77, 0.85'
            load, _, _ = get_subprocess_output(["uptime"], self.log)
            load = load.strip().split(' ')
            load = [float(load[-3].strip(',')),
                    float(load[-2].strip(',')),
                    float(load[-1].strip(','))]

        self.gauge('system.load.1', load[0])
        self.gauge('system.load.5', load[1])
        self.gauge('system.load.15', load[2])

        # Normalize load by number of cores
        cores = psutil.cpu_count()
        assert cores >= 1, "Cannot determine number of cores"

        self.gauge('system.load.norm.1', load[0]/cores)
        self.gauge('system.load.norm.5', load[1]/cores)
        self.gauge('system.load.norm.15', load[2]/cores)
