# checks/corechecks/system/filesystem/filesystem.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from utils.process import get_subprocess_output
from checks import AgentCheck


class FilesystemCheck(AgentCheck):
    """
    Core filesystem capacity check.

    Parses POSIX df -P output and emits metrics in MB.
    """

    KB = 1 << 10  # convert MB to KB divisor

    __slots__ = tuple()

    def check(self, instance):
        # POSIX portable format (MB units)
        output, _, _ = get_subprocess_output(['df', '-P'], self.log)

        '''
        Filesystem    MB blocks      Used Available Capacity Mounted on
        /dev/hd4         768.00    304.84    463.16      40% /
        /dev/hd2        8448.00   2583.39   5864.61      31% /usr
        /dev/hd9var      768.00    655.57    112.43      86% /var
        /dev/hd3         256.00    158.39     97.61      62% /tmp
        /dev/hd1         256.00    219.11     36.89      86% /home
        '''
        lines = [l for l in output.splitlines() if l]
        for line in lines[1:]:  # skip header
            fields = [f for f in line.split(' ') if f]

            filesystem = '_'.join(fields[0:-5])

            try:
                blocks = float(fields[-5])
                used = float(fields[-4])
                available = float(fields[-3])
            except ValueError:
                self.log.debug("Unable to get stats for %s - skipping", filesystem)
                continue

            mount = fields[-1]

            tags = ['fs:{}'.format(filesystem), 'mount:{}'.format(mount)]

            self.gauge('system.fs.total', round(blocks / self.KB), tags=tags)
            self.gauge('system.fs.used', round(used / self.KB), tags=tags)
            self.gauge('system.fs.available', round(available / self.KB), tags=tags)

            try:
                self.gauge('system.fs.available.pct', (used / blocks) * 100, tags=tags)
            except ZeroDivisionError:
                self.gauge('system.fs.available.pct', 100, tags=tags)
