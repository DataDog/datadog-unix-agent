# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import time

import psutil

from checks import AgentCheck


class Cpu(AgentCheck):

    def __init__(self, *args, **kwargs):
        super(Cpu, self).__init__(*args, **kwargs)
        self._last = None
        self._last_ts = None
        self._nb_cpu = psutil.cpu_count()
        self._ticks_per_sec = os.sysconf("SC_CLK_TCK")

    def check(self, instance):
        res = psutil.cpu_times()
        now = time.time()

        if self._last:
            delta = now - self._last_ts
            system = (res.system - self._last.system) / self._ticks_per_sec
            try:
                irq = (res.irq + res.softirq) - (self._last.irq + self._last.softirq)
                system += irq / self._ticks_per_sec
            except AttributeError:
                pass

            user = (res.user - self._last.user) / self._ticks_per_sec
            try:
                nice = (res.nice - self._last.nice)
                user += nice / self._ticks_per_sec
            except AttributeError:
                pass

            self.gauge("system.cpu.system", round(system / self._nb_cpu / delta * 100, 4))
            self.gauge("system.cpu.user", round(user / self._nb_cpu / delta * 100, 4))
            self.gauge("system.cpu.idle", round(
                (res.idle   - self._last.idle) / self._ticks_per_sec / self._nb_cpu / delta * 100, 4))

            if hasattr(res, 'iowait'):
                iowait = (res.iowait   - self._last.iowait) / self._ticks_per_sec
                self.gauge("system.cpu.iowait", round(iowait / self._nb_cpu / delta * 100, 4))
            if hasattr(res, 'steal'):
                stolen = (res.steal  - self._last.steal) / self._ticks_per_sec
                self.gauge("system.cpu.stolen", round(stolen / self._nb_cpu / delta * 100, 4))
            if hasattr(res, 'guest'):
                guest = (res.guest  - self._last.guest) / self._ticks_per_sec
                self.gauge("system.cpu.guest", round(stolen / self._nb_cpu / delta * 100, 4))

        self._last = res
        self._last_ts = now
