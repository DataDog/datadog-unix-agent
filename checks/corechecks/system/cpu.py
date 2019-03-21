# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import psutil

from checks import AgentCheck


class Cpu(AgentCheck):
    PSUTIL_USAGE_ATTRS = ['idle', 'iowait', 'system', 'user', 'nice', 'irq',
                          'softirq', 'steal', 'guest', 'guest_nice']

    def __init__(self, *args, **kwargs):
        super(Cpu, self).__init__(*args, **kwargs)

    def check(self, instance):
        usage = psutil.cpu_times_percent(percpu=True)
        tags = instance.get('tags', [])
        for core_idx in range(len(usage)):
            metric_tags = tags+['core:{}'.format(core_idx)]
            core_usage = usage[core_idx]
            for attr in self.PSUTIL_USAGE_ATTRS:
                try:
                    value = getattr(core_usage, attr)
                    self.gauge("system.cpu.{}".format(attr), value, tags=metric_tags)
                except AttributeError:
                    self.log.debug('CPU usage attribute %s not available on this platform', attr)
                    pass
