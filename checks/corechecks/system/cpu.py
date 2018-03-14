# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import psutil

from checks import AgentCheck


class Cpu(AgentCheck):

    def __init__(self, *args, **kwargs):
        super(Cpu, self).__init__(*args, **kwargs)
        self._last = None
        self._nb_cpu = psutil.cpu_count()

    def check(self, instance):
        res = psutil.cpu_times()
        if self._last:
            system = (res.system + res.irq + res.softirq) - (self._last.system + self._last.irq + self._last.softirq)
            user = (res.user + res.nice) - (self._last.user + self._last.nice)

            self.gauge("system.cpu.system", round(system / self._nb_cpu, 4))
            self.gauge("system.cpu.user", round(user / self._nb_cpu, 4))
            self.gauge("system.cpu.wait", round((res.iowait - self._last.iowait) / self._nb_cpu, 4))
            self.gauge("system.cpu.idle", round((res.idle   - self._last.idle)   / self._nb_cpu, 4))
            self.gauge("system.cpu.stolen", round((res.steal  - self._last.steal)  / self._nb_cpu, 4))
            self.gauge("system.cpu.guest", round((res.guest  - self._last.guest)  / self._nb_cpu, 4))

        self._last = res
