import operator

from checks import AgentCheck
from utils.platform import Platform
from utils.get_subprocess import get_subprocess_output


class Cpu(AgentCheck):

    def check(self, instance):
        """
        Return an aggregate of CPU stats across all CPUs
        When figures are not available, False is sent back.
        """
        def format_results(us, sy, wa, idle, st, guest=None):
            data = {'user': us, 'system': sy, 'wait': wa, 'idle': idle, 'stolen': st, 'guest': guest}

            for k, v in data.iteritems():
                if v is not None:
                    self.gauge("system.cpu.%s" % k, v)

        def get_value(legend, data, name, filter_value=None):
            """
            Using the legend and a metric name, get the value or None from the data line
            """
            if name in legend:
                # locale-resilient float converter
                value = float(data[legend.index(name)].replace(",", "."))
                if filter_value is not None:
                    if value > filter_value:
                        return None
                return value

            else:
                # FIXME return a float or False, would trigger type error if not python
                self.log.debug("Cannot extract cpu value %s from %s (%s)" % (name, data, legend))
                return 0.0
        try:
            if Platform.is_linux():
                output, _, _ = get_subprocess_output(['mpstat', '1', '3'], self.log)
                # hack to remove default coloring from mpstat. Setting "S_COLOR=never" doesn't work
                output = output.replace("\x00", "")
                mpstat = output.splitlines()
                # topdog@ip:~$ mpstat 1 3
                # Linux 2.6.32-341-ec2 (ip)   01/19/2012  _x86_64_  (2 CPU)
                #
                # 04:22:41 PM  CPU    %usr   %nice    %sys %iowait    %irq   %soft  %steal  %guest   %idle
                # 04:22:42 PM  all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                # 04:22:43 PM  all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                # 04:22:44 PM  all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                # Average:     all    0.00    0.00    0.00    0.00    0.00    0.00    0.00    0.00  100.00
                #
                # OR
                #
                # Thanks to Mart Visser to spotting this one.
                # blah:/etc/dd-agent# mpstat
                # Linux 2.6.26-2-xen-amd64 (atira)  02/17/2012  _x86_64_
                #
                # 05:27:03 PM  CPU    %user   %nice   %sys %iowait    %irq   %soft  %steal  %idle   intr/s
                # 05:27:03 PM  all    3.59    0.00    0.68    0.69    0.00   0.00    0.01   95.03    43.65
                #
                legend = [l for l in mpstat if "%usr" in l or "%user" in l]
                avg = [l for l in mpstat if "Average" in l]
                if len(legend) == 1 and len(avg) == 1:
                    headers = [h for h in legend[0].split() if h not in ("AM", "PM")]
                    data = avg[0].split()

                    # Userland
                    # Debian lenny says %user so we look for both
                    # One of them will be 0
                    cpu_metrics = {
                        "%usr": None, "%user": None, "%nice": None,
                        "%iowait": None, "%idle": None, "%sys": None,
                        "%irq": None, "%soft": None, "%steal": None,
                        "%guest": None
                    }

                    for cpu_m in cpu_metrics:
                        cpu_metrics[cpu_m] = get_value(headers, data, cpu_m, filter_value=110)

                    if any([v is None for v in cpu_metrics.values()]):
                        self.log.warning("Invalid mpstat data: %s" % data)

                    cpu_user = cpu_metrics["%usr"] + cpu_metrics["%user"] + cpu_metrics["%nice"]
                    cpu_system = cpu_metrics["%sys"] + cpu_metrics["%irq"] + cpu_metrics["%soft"]
                    cpu_wait = cpu_metrics["%iowait"]
                    cpu_idle = cpu_metrics["%idle"]
                    cpu_stolen = cpu_metrics["%steal"]
                    cpu_guest = cpu_metrics["%guest"]

                    format_results(cpu_user,
                                   cpu_system,
                                   cpu_wait,
                                   cpu_idle,
                                   cpu_stolen,
                                   cpu_guest)

            elif Platform.is_freebsd():
                # generate 3 seconds of data
                # tty            ada0              cd0            pass0             cpu
                # tin  tout  KB/t tps  MB/s   KB/t tps  MB/s   KB/t tps  MB/s  us ni sy in id
                # 0    69 26.71   0  0.01   0.00   0  0.00   0.00   0  0.00   2  0  0  1 97
                # 0    78  0.00   0  0.00   0.00   0  0.00   0.00   0  0.00   0  0  0  0 100
                iostats, _, _ = get_subprocess_output(['iostat', '-w', '3', '-c', '2'], self.log)
                lines = [l for l in iostats.splitlines() if len(l) > 0]
                legend = [l for l in lines if "us" in l]
                if len(legend) == 1:
                    headers = legend[0].split()
                    data = lines[-1].split()
                    cpu_user = get_value(headers, data, "us")
                    cpu_nice = get_value(headers, data, "ni")
                    cpu_sys = get_value(headers, data, "sy")
                    cpu_intr = get_value(headers, data, "in")
                    cpu_wait = 0
                    cpu_idle = get_value(headers, data, "id")
                    cpu_stol = 0
                    format_results(cpu_user + cpu_nice, cpu_sys + cpu_intr, cpu_wait, cpu_idle, cpu_stol)

                else:
                    self.log.warn("Expected to get at least 4 lines of data from iostat instead of just " + str(iostats[:max(80, len(iostats))]))

            elif Platform.is_solaris():
                # mpstat -aq 1 2
                # SET minf mjf xcal  intr ithr  csw icsw migr smtx  srw syscl  usr sys  wt idl sze
                # 0 5239   0 12857 22969 5523 14628   73  546 4055    1 146856    5   6   0  89  24 <-- since boot
                # 1 ...
                # SET minf mjf xcal  intr ithr  csw icsw migr smtx  srw syscl  usr sys  wt idl sze
                # 0 20374   0 45634 57792 5786 26767   80  876 20036    2 724475   13  13   0  75  24 <-- past 1s
                # 1 ...
                # http://docs.oracle.com/cd/E23824_01/html/821-1462/mpstat-1m.html
                #
                # Will aggregate over all processor sets
                    output, _, _ = get_subprocess_output(['mpstat', '-aq', '1', '2'], self.log)
                    mpstat = output.splitlines()
                    lines = [l for l in mpstat if len(l) > 0]
                    # discard the first len(lines)/2 lines
                    lines = lines[len(lines)/2:]
                    legend = [l for l in lines if "SET" in l]
                    assert len(legend) == 1
                    if len(legend) == 1:
                        headers = legend[0].split()
                        # collect stats for each processor set
                        # and aggregate them based on the relative set size
                        d_lines = [l for l in lines if "SET" not in l]
                        user = [get_value(headers, l.split(), "usr") for l in d_lines]
                        kern = [get_value(headers, l.split(), "sys") for l in d_lines]
                        wait = [get_value(headers, l.split(), "wt") for l in d_lines]
                        idle = [get_value(headers, l.split(), "idl") for l in d_lines]
                        size = [get_value(headers, l.split(), "sze") for l in d_lines]
                        count = sum(size)
                        rel_size = [s/count for s in size]
                        dot = lambda v1, v2: reduce(operator.add, map(operator.mul, v1, v2))
                        format_results(dot(user, rel_size),
                                       dot(kern, rel_size),
                                       dot(wait, rel_size),
                                       dot(idle, rel_size),
                                       0.0)
            else:
                self.log.warn("CPUStats: unsupported platform")
        except Exception:
            self.log.exception("Cannot compute CPU stats")
