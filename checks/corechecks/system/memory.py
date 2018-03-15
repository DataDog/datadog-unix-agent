import re

from checks import AgentCheck
from utils.platform import Platform
from utils.get_subprocess import get_subprocess_output


class Memory(AgentCheck):

    def format_results(self, name, results):
        for k, v in results.iteritems():
            if v is not None:
                self.gauge("system.%s.%s" % (name, k), v)

    def check(self, instance):
        if Platform.is_linux():
            proc_location = '/proc'
            try:
                proc_meminfo = "{}/meminfo".format(proc_location)
                with open(proc_meminfo, 'r') as mem_info:
                    lines = mem_info.readlines()
            except Exception:
                self.log.exception('Cannot get memory metrics from %s', proc_meminfo)
                return

            # NOTE: not all of the stats below are present on all systems as
            # not all kernel versions report all of them.

            regexp = re.compile(r'^(\w+):\s+([0-9]+)')  # We run this several times so one-time compile now
            meminfo = {}

            parse_error = False
            for line in lines:
                try:
                    match = re.search(regexp, line)
                    if match is not None:
                        meminfo[match.group(1)] = match.group(2)
                except Exception:
                    parse_error = True
            if parse_error:
                self.log.error("Error parsing %s", proc_meminfo)

            memData = {}
            swapData = {}

            # Physical memory
            # FIXME units are in MB, we should use bytes instead
            try:
                memData['total'] = int(meminfo.get('MemTotal', 0)) / 1024
                memData['free'] = int(meminfo.get('MemFree', 0)) / 1024
                memData['buffers'] = int(meminfo.get('Buffers', 0)) / 1024
                memData['cached'] = int(meminfo.get('Cached', 0)) / 1024
                memData['shared'] = int(meminfo.get('Shmem', 0)) / 1024
                memData['slab'] = int(meminfo.get('Slab', 0)) / 1024
                memData['page_tables'] = int(meminfo.get('PageTables', 0)) / 1024
                memData['used'] = memData['total'] - memData['free']

                if 'MemAvailable' in meminfo:
                    memData['usable'] = int(meminfo.get('MemAvailable', 0)) / 1024
                else:
                    # Usable is relative since cached and buffers are actually used to speed things up.
                    memData['usable'] = memData['free'] + memData['buffers'] + memData['cached']

                if memData['total'] > 0:
                    memData['pct_usable'] = float(memData['usable']) / float(memData['total'])
            except Exception:
                self.log.exception('Cannot compute stats from %s', proc_meminfo)

            # Swap
            # FIXME units are in MB, we should use bytes instead
            try:
                swapData['total'] = int(meminfo.get('SwapTotal', 0)) / 1024
                swapData['free'] = int(meminfo.get('SwapFree', 0)) / 1024
                swapData['cached'] = int(meminfo.get('SwapCached', 0)) / 1024
                swapData['used'] = swapData['total'] - swapData['free']

                if swapData['total'] > 0:
                    swapData['pct_free'] = float(swapData['free']) / float(swapData['total'])
            except Exception:
                self.log.exception('Cannot compute swap stats')

            self.format_results('mem', memData)
            self.format_results('swap', swapData)
        elif Platform.is_freebsd():
            try:
                output, _, _ = get_subprocess_output(['sysctl', 'vm.stats.vm'], self.log)
                sysctl = output.splitlines()
            except Exception:
                self.log.exception('getMemoryUsage')
                return

            # ...
            # vm.stats.vm.v_page_size: 4096
            # vm.stats.vm.v_page_count: 759884
            # vm.stats.vm.v_wire_count: 122726
            # vm.stats.vm.v_active_count: 109350
            # vm.stats.vm.v_cache_count: 17437
            # vm.stats.vm.v_inactive_count: 479673
            # vm.stats.vm.v_free_count: 30542
            # ...

            # We run this several times so one-time compile now
            regexp = re.compile(r'^vm\.stats\.vm\.(\w+):\s+([0-9]+)')
            meminfo = {}

            parse_error = False
            for line in sysctl:
                try:
                    match = re.search(regexp, line)
                    if match is not None:
                        meminfo[match.group(1)] = match.group(2)
                except Exception:
                    parse_error = True
            if parse_error:
                self.log.error("Error parsing vm.stats.vm output: %s", sysctl)

            memData = {}
            swapData = {}

            # Physical memory
            try:
                pageSize = int(meminfo.get('v_page_size'))

                memData['total'] = (int(meminfo.get('v_page_count', 0))
                                    * pageSize) / 1048576
                memData['free'] = (int(meminfo.get('v_free_count', 0))
                                   * pageSize) / 1048576
                memData['cached'] = (int(meminfo.get('v_cache_count', 0))
                                     * pageSize) / 1048576
                memData['used'] = ((int(meminfo.get('v_active_count'), 0) +
                                    int(meminfo.get('v_wire_count', 0)))
                                   * pageSize) / 1048576
                memData['usable'] = ((int(meminfo.get('v_free_count'), 0) +
                                          int(meminfo.get('v_cache_count', 0)) +
                                          int(meminfo.get('v_inactive_count', 0))) *
                                         pageSize) / 1048576

                if memData['total'] > 0:
                    memData['pct_usable'] = float(memData['usable']) / float(memData['total'])
            except Exception:
                self.log.exception('Cannot compute stats from %s', proc_meminfo)

            # Swap
            try:
                output, _, _ = get_subprocess_output(['swapinfo', '-m'], self.log)
                sysctl = output.splitlines()
            except Exception:
                self.log.exception('getMemoryUsage')
                return

            # ...
            # Device          1M-blocks     Used    Avail Capacity
            # /dev/ad0s1b           570        0      570     0%
            # ...

            assert "Device" in sysctl[0]

            try:
                swapData['total'] = 0
                swapData['free'] = 0
                swapData['used'] = 0
                for line in sysctl[1:]:
                    if len(line) > 0:
                        line = line.split()
                        swapData['total'] += int(line[1])
                        swapData['free'] += int(line[3])
                        swapData['used'] += int(line[2])
            except Exception:
                self.log.exception('Cannot compute stats from swapinfo')

            self.format_results('mem', memData)
            self.format_results('swap', swap)
        elif Platform.is_solaris():
            try:
                memData = {}
                swapData = {}
                cmd = ["kstat", "-m", "memory_cap", "-c", "zone_memory_cap", "-p"]
                output, _, _ = get_subprocess_output(cmd, self.log)
                kmem = output.splitlines()

                # turn memory_cap:360:zone_name:key value
                # into { "key": value, ...}
                kv = [l.strip().split() for l in kmem if len(l) > 0]
                entries = dict([(k.split(":")[-1], v) for (k, v) in kv])
                # extract rss, physcap, swap, swapcap, turn into MB
                convert = lambda v: int(long(v))/2**20
                memData["total"] = convert(entries["physcap"])
                memData["used"] = convert(entries["rss"])
                memData["free"] = memData["total"] - memData["used"]
                swapData["total"] = convert(entries["swapcap"])
                swapData["used"] = convert(entries["swap"])
                swapData["free"] = swapData["total"] - swapData["used"]

                if swapData['total'] > 0:
                    swapData['pct_free'] = float(swapData['free']) / float(swapData['total'])
                self.format_results('mem', memData)
                self.format_results('swap', swapData)
            except Exception:
                self.log.exception("Cannot compute mem stats from kstat -c zone_memory_cap")
                return
