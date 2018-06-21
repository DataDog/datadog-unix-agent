# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import uptime

from utils.process import get_subprocess_output
from checks import AgentCheck


class UptimeCheck(AgentCheck):

    def check(self, instance):
        up = uptime.uptime()
        if up:
            self.gauge("system.uptime", up)
            return

        # On AIX and some other platforms the uptime module may fail to find the system
        # uptime and return `None` - in that case, grab the uptime as the init process
        # (pid 1) uptime
        try:
            # get uptime from init process lifetime (pid 1)
            # format: 8-00:56:09
            up, _, _ = get_subprocess_output(['ps', '-o', 'etime=', '-p1'], self.log)
            up = up.split('-')
            if len(up) == 1:
                days, rest = 0, up[0]
            else:
                days, rest = up[0], up[1]

            time = rest.split(':')
            days_s = int(days) * 24 * 60 * 60
            hour_s = int(time[0]) * 60 * 60
            mins_s = int(time[1]) * 60
            secs = int(time[2])
            self.gauge("system.uptime", days_s+hour_s+mins_s+secs)
        except Exception:
            self.log.exception("Cannot collect uptime statistics")
