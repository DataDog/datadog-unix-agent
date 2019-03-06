# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import sys
import time

import psutil

from checks import AgentCheck
from utils.process import get_subprocess_output


class Cpu(AgentCheck):
    _IOSTAT_MAP = {
        'iowait': 5,
        'physc': 6,
        'entc': 7,
    }

    def __init__(self, *args, **kwargs):
        super(Cpu, self).__init__(*args, **kwargs)
        self._last = None
        self._last_ts = None
        self._nb_cpu = psutil.cpu_count()
        self._ticks_per_sec = os.sysconf("SC_CLK_TCK")
        self._tick_factor = self._ticks_per_sec if sys.platform.startswith('aix') else 1

    def check(self, instance):
        res = psutil.cpu_times()
        ts = time.time()

        if self._last:
            delta = ts - self._last_ts

            system = (res.system - self._last.system) / self._tick_factor
            try:
                # TODO: figure out if res.irq and res.softirq need to be in
                #       in ticks/s
                system += ((res.irq + res.softirq) - (self._last.irq + self._last.softirq)) / self._tick_factor
            except AttributeError:
                pass

            system = system / delta * 100

            user = (res.user - self._last.user) / self._tick_factor
            try:
                # TODO: figure out if res.nice needs to be in ticks/s
                user += (res.nice - self._last.nice) / self._tick_factor
            except AttributeError:
                pass

            user = user / delta * 100

            self.gauge("system.cpu.system", round(system / self._nb_cpu, 4))
            self.gauge("system.cpu.user", round(user / self._nb_cpu, 4))
            idle = (res.idle - self._last.idle) / self._tick_factor / delta * 100
            self.gauge("system.cpu.idle", round(idle / self._nb_cpu, 4))

            collect_iowait = True
            if hasattr(res, 'iowait'):
                iowait = (res.iowait - self._last.iowait) / delta / self._nb_cpu * 100
                self.gauge("system.cpu.iowait", round(iowait, 4))
                collect_iowait = False

            if hasattr(res, 'steal'):
                stolen = (res.steal - self._last.steal) / delta / self._nb_cpu * 100
                self.gauge("system.cpu.stolen", round(stolen, 4))

            if hasattr(res, 'guest'):
                guest = (res.guest - self._last.guest) / delta / self._nb_cpu * 100
                self.gauge("system.cpu.guest", round(guest, 4))

            self._collect_iostat(iowait=collect_iowait)

        self._last = res
        self._last_ts = ts

    def _collect_iostat(self, iowait=False):
        # iowait sample output:
        #
        # System configuration: lcpu=8 drives=1 ent=0.40 paths=2 vdisks=2
        #
        # tty:      tin         tout    avg-cpu: % user % sys % idle % iowait physc % entc
        #         0.0          0.8                0.0   0.0  100.0      0.0   0.0    0.1
        #
        # Disks:         % tm_act     Kbps      tps    Kb_read   Kb_wrtn
        # hdisk11           0.0       0.8       0.1     919576  14296158

        output, _, _ = get_subprocess_output(['iostat'], self.log)
        stats = [_f for _f in output.splitlines() if _f]
        fields = [field for field in stats[2].split(' ') if field]

        for metric, idx in self._IOSTAT_MAP.items():
            if metric == "iowait" and not iowait:
                continue

            self.gauge("system.cpu.{}".format(metric), round(float(fields[idx]), 4))
