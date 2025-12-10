# checks/corechecks/system/filesystem/filesystem.py
# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.

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

            tags = [f"fs:{filesystem}", f"mount:{mount}"]

            self.gauge('system.fs.total', round(blocks / self.KB), tags=tags)
            self.gauge('system.fs.used', round(used / self.KB), tags=tags)
            self.gauge('system.fs.available', round(available / self.KB), tags=tags)

            try:
                self.gauge('system.fs.available.pct', (used / blocks) * 100, tags=tags)
            except ZeroDivisionError:
                self.gauge('system.fs.available.pct', 100, tags=tags)
