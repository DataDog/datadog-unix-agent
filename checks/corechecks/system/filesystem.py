# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from utils.process import get_subprocess_output
from checks import AgentCheck


class Filesystem(AgentCheck):

    def check(self, instance):
        # -P  for POSIX portable format
        # units are in MB
        output, _, _ = get_subprocess_output(['df', '-P', '-m'], self.log)

        '''
        Filesystem    MB blocks      Used Available Capacity Mounted on
        /dev/hd4         768.00    304.84    463.16      40% /
        /dev/hd2        8448.00   2583.39   5864.61      31% /usr
        /dev/hd9var      768.00    655.57    112.43      86% /var
        /dev/hd3         256.00    158.39     97.61      62% /tmp
        /dev/hd1         256.00    219.11     36.89      86% /home
        '''
        stats = [_f for _f in output.splitlines() if _f]
        for line in stats[1:]:
            fields = line.split(' ')
            fields = [_f for _f in fields if _f]
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
            self.gauge('system.fs.total', blocks, tags=tags)
            self.gauge('system.fs.used', used, tags=tags)
            self.gauge('system.fs.available', available, tags=tags)
            try:
                self.gauge('system.fs.available.pct', (used/blocks)*100, tags=tags)
            except ZeroDivisionError:
                self.gauge('system.fs.available.pct', 100, tags=tags)
