# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.
from __future__ import division

import psutil
from checks import AgentCheck


class Memory(AgentCheck):

    def check(self, instance):
        # units are in byte, we use MB instead
        to_mb = lambda x: round(int(x) / (1 << 20))

        mem = psutil.virtual_memory()
        self.gauge("system.mem.total", to_mb(mem.total))
        self.gauge("system.mem.free", to_mb(mem.free))
        self.gauge("system.mem.used", to_mb(mem.total - mem.free))
        self.gauge("system.mem.usable", to_mb(mem.available))
        if mem.total > 0:
            self.gauge("system.mem.pct_usable", round(mem.available / mem.total, 4))

        swap = psutil.swap_memory()
        self.gauge("system.swap.total", to_mb(swap.total))
        self.gauge("system.swap.free", to_mb(swap.free))
        self.gauge("system.swap.used", to_mb(swap.used))
        if swap.total > 0:
            self.gauge("system.swap.pct_free", round(swap.free / swap.total, 2))
