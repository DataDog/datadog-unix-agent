# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import psutil

from checks import AgentCheck

class Load(AgentCheck):

    def check(self, instance):
        load = os.getloadavg()
        self.gauge('system.load.1', load[0])
        self.gauge('system.load.5', load[1])
        self.gauge('system.load.15', load[2])

        # Normalize load by number of cores
        cores = psutil.cpu_count()
        assert cores >= 1, "Cannot determine number of cores"

        self.gauge('system.load.norm.1', load[0]/cores)
        self.gauge('system.load.norm.5', load[1]/cores)
        self.gauge('system.load.norm.15', load[2]/cores)
