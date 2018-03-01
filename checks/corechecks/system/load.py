import re

from checks import AgentCheck
from utils.platform import Platform
from utils.get_subprocess import get_subprocess_output
import config

class Load(AgentCheck):

    def check(self, instance):
        if Platform.is_linux():
            proc_location = '/proc'
            try:
                proc_loadavg = "{}/loadavg".format(proc_location)
                with open(proc_loadavg, 'r') as load_avg:
                    uptime = load_avg.readline().strip()
            except Exception:
                self.log.exception('Cannot extract load')
                return False

        elif Platform.is_solaris() or Platform.is_freebsd():
            # Get output from uptime
            try:
                uptime, _, _ = get_subprocess_output(['uptime'], self.log)
            except Exception:
                self.log.exception('Cannot extract load')
                return False

        # Split out the 3 load average values
        load = [res.replace(',', '.') for res in re.findall(r'([0-9]+[\.,]\d+)', uptime)]
        # Normalize load by number of cores
        try:
            cores = int(config.agent_config.get('system_stats').get('cpuCores'))
            assert cores >= 1, "Cannot determine number of cores"
            # Compute a normalized load, named .load.norm to make it easy to find next to .load
            self.gauge('system.load.1', float(load[0]))
            self.gauge('system.load.5', float(load[1]))
            self.gauge('system.load.15', float(load[2]))
            self.gauge('system.load.norm.1', float(load[0])/cores)
            self.gauge('system.load.norm.5', float(load[1])/cores)
            self.gauge('system.load.norm.15', float(load[2])/cores)
        except Exception:
            # No normalized load available
            self.gauge('system.load.1', float(load[0]))
            self.gauge('system.load.5', float(load[1]))
            self.gauge('system.load.15', float(load[2]))
