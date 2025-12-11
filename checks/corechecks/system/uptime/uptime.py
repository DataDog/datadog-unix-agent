# checks/corechecks/system/uptime/uptime.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import uptime

from checks import AgentCheck
from utils.process import get_subprocess_output
from .__about__ import __version__

class UptimeCheck(AgentCheck):
    __version__ = __version__
    """
    Core system uptime check.

    Tries python-uptime; if unavailable, falls back to PID 1 elapsed time.
    """

    __slots__ = tuple()

    def check(self, instance):
        # Attempt python-uptime first
        up = None
        if uptime is not None:
            try:
                up = uptime.uptime()
            except Exception:
                pass

        if up is not None:
            self.gauge("system.uptime", up)
            return

        # Fallback path: parse PID 1 elapsed time
        try:
            etime, _, _ = get_subprocess_output(['ps', '-o', 'etime=', '-p1'], self.log)
            etime = etime.strip()

            if '-' in etime:
                days_str, hms_str = etime.split('-')
                days = int(days_str)
            else:
                days = 0
                hms_str = etime

            parts = hms_str.split(':')
            if len(parts) == 2:
                hours = 0
                minutes, seconds = map(int, parts)
            else:
                hours, minutes, seconds = map(int, parts)

            total_seconds = (
                days * 86400 +
                hours * 3600 +
                minutes * 60 +
                seconds
            )

            self.gauge("system.uptime", total_seconds)

        except Exception:
            self.log.exception("Cannot collect uptime statistics")
