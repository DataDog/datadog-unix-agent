# checks/corechecks/system/cpu/cpu.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.

import psutil
from checks import AgentCheck


class CpuCheck(AgentCheck):
    """
    Core CPU check measuring per-core CPU usage percentages.
    """

    __slots__ = ("first_run",)

    PSUTIL_USAGE_ATTRS = [
        'idle', 'iowait', 'system', 'user',
        'nice', 'irq', 'softirq', 'steal',
        'guest', 'guest_nice'
    ]

    def __init__(self, *args, **kwargs):
        super(CpuCheck, self).__init__(*args, **kwargs)
        self.first_run = True

    def check(self, instance):
        usage = psutil.cpu_times_percent(percpu=True)
        tags = instance.get('tags', []) or []

        for core_idx, core_usage in enumerate(usage):
            metric_tags = tags + [f'core:{core_idx}']

            for attr in self.PSUTIL_USAGE_ATTRS:
                try:
                    value = getattr(core_usage, attr)
                except AttributeError:
                    if self.first_run:
                        self.log.debug(
                            "CPU usage attribute %s not available on this platform",
                            attr
                        )
                    continue

                self.gauge(f"system.cpu.{attr}", value, tags=metric_tags)

        self.first_run = False
