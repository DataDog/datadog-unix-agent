# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
from collections import defaultdict
import time

# 3p
import psutil

# project
from checks import AgentCheck


DEFAULT_AD_CACHE_DURATION = 120
DEFAULT_PID_CACHE_DURATION = 120


ATTR_TO_METRIC = {
    'thr':              'threads',
    'cpu':              'cpu.pct',
    'cpu_norm':         'cpu.normalized_pct',
    'rss':              'mem.rss',
    'vms':              'mem.vms',
    'real':             'mem.real',
    'open_fd':          'open_file_descriptors',
    'r_count':          'io.r_count',
    'w_count':          'io.w_count',
    'r_bytes':          'io.r_bytes',
    'w_bytes':          'io.w_bytes',
    'ctx_swtch_vol':    'ctx_swt.voluntary',
    'ctx_swtch_invol':  'ctx_swt.involuntary',
    'run_time':         'run_time',
    'mem_pct':          'mem.pct'
}


class Process(AgentCheck):
    def __init__(self, name, init_config, instance, aggregator=None):
        AgentCheck.__init__(self, name, init_config, instance, aggregator)

        # ad stands for access denied
        # We cache the PIDs getting this error and don't iterate on them more often than `access_denied_cache_duration``
        # This cache is for all PIDs so it's global, but it should be refreshed by instance
        self.last_ad_cache_ts = {}
        self.ad_cache = set()
        self.access_denied_cache_duration = int(
            init_config.get(
                'access_denied_cache_duration',
                DEFAULT_AD_CACHE_DURATION
            )
        )

        # By default cache the PID list for a while
        # Sometimes it's not wanted b/c it can mess with no-data monitoring
        # This cache is indexed per instance
        self.last_pid_cache_ts = {}
        self.pid_cache = {}
        self.pid_cache_duration = int(
            init_config.get(
                'pid_cache_duration',
                DEFAULT_PID_CACHE_DURATION
            )
        )

        # Process cache, indexed by instance
        self.process_cache = defaultdict(dict)

    def should_refresh_ad_cache(self, name):
        now = time.time()
        return now - self.last_ad_cache_ts.get(name, 0) > self.access_denied_cache_duration

    def should_refresh_pid_cache(self, name):
        now = time.time()
        return now - self.last_pid_cache_ts.get(name, 0) > self.pid_cache_duration

    def find_pids(self, name, search_string, exact_match, ignore_ad=True):
        """
        Create a set of pids of selected processes.
        Search for search_string
        """
        if not self.should_refresh_pid_cache(name):
            return self.pid_cache[name]

        ad_error_logger = self.log.debug
        if not ignore_ad:
            ad_error_logger = self.log.error

        refresh_ad_cache = self.should_refresh_ad_cache(name)

        matching_pids = set()

        for proc in psutil.process_iter():
            # Skip access denied processes
            if not refresh_ad_cache and proc.pid in self.ad_cache:
                continue

            found = False
            for string in search_string:
                try:
                    if string == 'All':
                        found = True
                    elif exact_match:
                        if proc.name() == string:
                            found = True
                    else:
                        cmdline = proc.cmdline()
                        if string in ' '.join(cmdline):
                            found = True

                except psutil.NoSuchProcess:
                    self.log.warning('Process disappeared while scanning')
                except psutil.AccessDenied as e:
                    ad_error_logger('Access denied to process with PID {}'.format(proc.pid))
                    ad_error_logger('Error: {}'.format(e))
                    if refresh_ad_cache:
                        self.ad_cache.add(proc.pid)
                    if not ignore_ad:
                        raise
                else:
                    if refresh_ad_cache:
                        self.ad_cache.discard(proc.pid)
                    if found:
                        matching_pids.add(proc.pid)
                        break

        self.pid_cache[name] = matching_pids
        self.last_pid_cache_ts[name] = time.time()
        if refresh_ad_cache:
            self.last_ad_cache_ts[name] = time.time()
        return matching_pids

    def psutil_wrapper(self, process, method, accessors, *args, **kwargs):
        """
        A psutil wrapper that is calling
        * psutil.method(*args, **kwargs) and returns the result
        OR
        * psutil.method(*args, **kwargs).accessor[i] for each accessors
        given in a list, the result being indexed in a dictionary
        by the accessor name
        """

        if accessors is None:
            result = None
        else:
            result = {}

        # Ban certain method that we know fail
        if method == 'num_handles':
            return result

        try:
            res = getattr(process, method)(*args, **kwargs)
            if accessors is None:
                result = res
            else:
                for acc in accessors:
                    try:
                        result[acc] = getattr(res, acc)
                    except AttributeError:
                        self.log.debug("psutil.%s().%s attribute does not exist", method, acc)
        except (NotImplementedError, AttributeError):
            self.log.debug("psutil method %s not implemented", method)
        except psutil.AccessDenied:
            self.log.debug("psutil was denied access for method %s", method)
        except psutil.NoSuchProcess:
            self.warning("Process {} disappeared while scanning".format(process.pid))

        return result

    def get_process_state(self, name, pids):
        st = defaultdict(list)

        # Remove from cache the processes that are not in `pids`
        cached_pids = set(self.process_cache[name].keys())
        pids_to_remove = cached_pids - pids
        for pid in pids_to_remove:
            del self.process_cache[name][pid]

        for pid in pids:
            st['pids'].append(pid)

            new_process = False
            # If the pid's process is not cached, retrieve it
            if (pid not in self.process_cache[name] or not self.process_cache[name][pid].is_running()):
                new_process = True
                try:
                    self.process_cache[name][pid] = psutil.Process(pid)
                    self.log.debug('New process in cache: %s', pid)
                # Skip processes dead in the meantime
                except psutil.NoSuchProcess:
                    self.warning("Process {} disappeared while scanning".format(pid))
                    # reset the PID cache now, something changed
                    self.last_pid_cache_ts[name] = 0
                    continue

            p = self.process_cache[name][pid]

            meminfo = self.psutil_wrapper(p, 'memory_info', ['rss', 'vms'])
            st['rss'].append(meminfo.get('rss'))
            st['vms'].append(meminfo.get('vms'))
            st['real'].append(None)

            mem_percent = self.psutil_wrapper(p, 'memory_percent', None)
            st['mem_pct'].append(mem_percent)

            ctxinfo = self.psutil_wrapper(p, 'num_ctx_switches', ['voluntary', 'involuntary'])
            st['ctx_swtch_vol'].append(ctxinfo.get('voluntary'))
            st['ctx_swtch_invol'].append(ctxinfo.get('involuntary'))

            st['thr'].append(self.psutil_wrapper(p, 'num_threads', None))

            cpu_percent = self.psutil_wrapper(p, 'cpu_percent', None)
            cpu_count = psutil.cpu_count()
            if not new_process:
                # psutil returns `0.` for `cpu_percent` the
                # first time it's sampled on a process,
                # so save the value only on non-new processes
                st['cpu'].append(cpu_percent)
                if cpu_count > 0 and cpu_percent is not None:
                    st['cpu_norm'].append(cpu_percent/cpu_count)
                else:
                    self.log.debug('could not calculate the normalized '
                                   'cpu pct, cpu_count: %s', cpu_count)
            st['open_fd'].append(self.psutil_wrapper(p, 'num_fds', None))

            ioinfo = self.psutil_wrapper(p, 'io_counters',
                                         ['read_count', 'write_count', 'read_bytes', 'write_bytes'])
            st['r_count'].append(ioinfo.get('read_count'))
            st['w_count'].append(ioinfo.get('write_count'))
            st['r_bytes'].append(ioinfo.get('read_bytes'))
            st['w_bytes'].append(ioinfo.get('write_bytes'))

            # calculate process run time
            create_time = self.psutil_wrapper(p, 'create_time', None)
            if create_time is not None:
                now = time.time()
                run_time = now - create_time
                st['run_time'].append(run_time)

        return st

    def _get_child_processes(self, pids):
        children_pids = set()
        for pid in pids:
            try:
                children = psutil.Process(pid).children(recursive=True)
                self.log.debug('%s children were collected for process %s', len(children), pid)
                for child in children:
                    children_pids.add(child.pid)
            except psutil.NoSuchProcess:
                pass

        return children_pids

    def check(self, instance):
        name = instance.get('name', None)
        tags = instance.get('tags', [])
        exact_match = instance.get('exact_match', True)
        search_string = instance.get('search_string', None)
        ignore_ad = instance.get('ignore_denied_access', True)
        pid = instance.get('pid')
        pid_file = instance.get('pid_file')
        collect_children = instance.get('collect_children', False)
        user = instance.get('user', False)

        if not isinstance(search_string, list) and pid is None and pid_file is None:
            raise ValueError('"search_string" or "pid" or "pid_file" parameter is required')

        # FIXME 6.x remove me
        if search_string is not None:
            if "All" in search_string:
                self.warning('Deprecated: Having "All" in your search_string will greatly reduce the '
                             'performance of the check and will be removed in a future version of the agent.')

        if name is None:
            raise KeyError('The "name" of process groups is mandatory')

        if pid is not None:
            # we use Process(pid) as a means to search, if pid not found
            # psutil.NoSuchProcess is raised.
            pids = self._get_pid_set(pid)
        elif pid_file is not None:
            try:
                with open(pid_file, 'r') as file_pid:
                    pid_line = file_pid.readline().strip()
                    pids = self._get_pid_set(int(pid_line))
            except IOError as e:
                # pid file doesn't exist, assuming the process is not running
                self.log.debug('Unable to find pid file: %s', e)
                pids = set()
        elif search_string is not None:
            pids = self.find_pids(
                name,
                search_string,
                exact_match,
                ignore_ad=ignore_ad
            )
        else:
            raise ValueError('The "search_string" or "pid" options are required for process identification')

        if collect_children:
            pids.update(self._get_child_processes(pids))

        if user:
            pids = self._filter_by_user(user, pids)

        proc_state = self.get_process_state(name, pids)

        # FIXME 6.x remove the `name` tag
        tags.extend(['process_name:{}'.format(name), name])

        self.log.debug('ProcessCheck: process %s analyzed', name)
        self.gauge('system.processes.number', len(pids), tags=tags)

        if len(pids) == 0:
            self.warning("No matching process '{}' was found".format(name))

        for attr, mname in ATTR_TO_METRIC.items():
            vals = [x for x in proc_state[attr] if x is not None]
            # skip []
            if vals:
                if attr == 'run_time':
                    self.gauge('system.processes.{}.avg'.format(mname), sum(vals)/len(vals), tags=tags)
                    self.gauge('system.processes.{}.max'.format(mname), max(vals), tags=tags)
                    self.gauge('system.processes.{}.min'.format(mname), min(vals), tags=tags)

                # FIXME 6.x: change this prefix?
                else:
                    self.gauge('system.processes.{}'.format(mname), sum(vals), tags=tags)

        self._process_service_check(name, len(pids), instance.get('thresholds', None), tags)

    def _get_pid_set(self, pid):
        try:
            return {psutil.Process(pid).pid}
        except psutil.NoSuchProcess:
            return set()

    def _process_service_check(self, name, nb_procs, bounds, tags):
        """
        Report a service check, for each process in search_string.
        Report as OK if the process is in the warning thresholds
                   CRITICAL             out of the critical thresholds
                   WARNING              out of the warning thresholds
        """
        # FIXME 6.x remove the `process:name` tag
        service_check_tags = tags + ["process:{}".format(name)]
        status = AgentCheck.OK
        status_str = {
            AgentCheck.OK: "OK",
            AgentCheck.WARNING: "WARNING",
            AgentCheck.CRITICAL: "CRITICAL"
        }

        if not bounds and nb_procs < 1:
            status = AgentCheck.CRITICAL
        elif bounds:
            warning = bounds.get('warning', [1, float('inf')])
            critical = bounds.get('critical', [1, float('inf')])

            if warning[1] < nb_procs or nb_procs < warning[0]:
                status = AgentCheck.WARNING
            if critical[1] < nb_procs or nb_procs < critical[0]:
                status = AgentCheck.CRITICAL

        self.service_check(
            "process.up",
            status,
            tags=service_check_tags,
            message="PROCS {}: {} processes found for {}".format(status_str[status], nb_procs, name)
        )

    def _filter_by_user(self, user, pids):
        """
        Filter pids by it's username.
        :param user: string with name of system user
        :param pids: set of pids to filter
        :return: set of filtered pids
        """
        filtered_pids = set()
        for pid in pids:
            try:
                proc = psutil.Process(pid)
                if proc.username() == user:
                    self.log.debug("Collecting pid %s belonging to %s", pid, user)
                    filtered_pids.add(pid)
                else:
                    self.log.debug("Discarding pid %s not belonging to %s", pid, user)
            except psutil.NoSuchProcess:
                pass

        return filtered_pids
