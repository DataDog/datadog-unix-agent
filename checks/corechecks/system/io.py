import re

from config import config
from checks import AgentCheck
from utils.platform import Platform
from utils.get_subprocess import get_subprocess_output


class Io(AgentCheck):

    def __init__(self, *args, **kwargs):
        super(Io, self).__init__(*args, **kwargs)
        self.header_re = re.compile(r'([%\\/\-_a-zA-Z0-9]+)[\s+]?')
        self.item_re = re.compile(r'^([\-a-zA-Z0-9\/]+)')
        self.value_re = re.compile(r'\d+\.\d+')

    def _parse_linux2(self, output):
        recentStats = output.split('Device')[2].split('\n')
        header = recentStats[0]
        headerNames = re.findall(self.header_re, header)
        device = None

        ioStats = {}

        for statsIndex in range(1, len(recentStats)):
            row = recentStats[statsIndex]

            if not row:
                # Ignore blank lines.
                continue

            deviceMatch = self.item_re.match(row)

            if deviceMatch is not None:
                # Sometimes device names span two lines.
                device = deviceMatch.groups()[0]
            else:
                continue

            values = re.findall(self.value_re, row)

            if not values:
                # Sometimes values are on the next line so we encounter
                # instances of [].
                continue

            ioStats[device] = {}

            for headerIndex in range(len(headerNames)):
                headerName = headerNames[headerIndex]
                ioStats[device][headerName] = values[headerIndex]

        return ioStats

    def xlate(self, metric_name, os_name):
        """Standardize on linux metric names"""
        if os_name == "sunos":
            names = {
                "wait": "await",
                "svc_t": "svctm",
                "%b": "%util",
                "kr/s": "rkB/s",
                "kw/s": "wkB/s",
                "actv": "avgqu-sz",
            }
        elif os_name == "freebsd":
            names = {
                "svc_t": "await",
                "%b": "%util",
                "kr/s": "rkB/s",
                "kw/s": "wkB/s",
                "wait": "avgqu-sz",
            }
        # translate if possible
        return names.get(metric_name, metric_name)

    def check(self, instance):
        """Capture io stats.

        @rtype dict
        @return {"device": {"metric": value, "metric": value}, ...}
        """
        io = {}
        try:
            if Platform.is_linux():
                stdout, _, _ = get_subprocess_output(['iostat', '-d', '1', '2', '-x', '-k'], self.log)

                #                 Linux 2.6.32-343-ec2 (ip-10-35-95-10)   12/11/2012      _x86_64_        (2 CPU)
                #
                # Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
                # sda1              0.00    17.61    0.26   32.63     4.23   201.04    12.48     0.16    4.81   0.53   1.73
                # sdb               0.00     2.68    0.19    3.84     5.79    26.07    15.82     0.02    4.93   0.22   0.09
                # sdg               0.00     0.13    2.29    3.84   100.53    30.61    42.78     0.05    8.41   0.88   0.54
                # sdf               0.00     0.13    2.30    3.84   100.54    30.61    42.78     0.06    9.12   0.90   0.55
                # md0               0.00     0.00    0.05    3.37     1.41    30.01    18.35     0.00    0.00   0.00   0.00
                #
                # Device:         rrqm/s   wrqm/s     r/s     w/s    rkB/s    wkB/s avgrq-sz avgqu-sz   await  svctm  %util
                # sda1              0.00     0.00    0.00   10.89     0.00    43.56     8.00     0.03    2.73   2.73   2.97
                # sdb               0.00     0.00    0.00    2.97     0.00    11.88     8.00     0.00    0.00   0.00   0.00
                # sdg               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                # sdf               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                # md0               0.00     0.00    0.00    0.00     0.00     0.00     0.00     0.00    0.00   0.00   0.00
                io.update(self._parse_linux2(stdout))

            elif Platform.is_solaris():
                output, _, _ = get_subprocess_output(["iostat", "-x", "-d", "1", "2"], self.log)
                iostat = output.splitlines()

                #                   extended device statistics <-- since boot
                # device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
                # ramdisk1    0.0    0.0    0.1    0.1  0.0  0.0    0.0   0   0
                # sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd1        79.9  149.9 1237.6 6737.9  0.0  0.5    2.3   0  11
                #                   extended device statistics <-- past second
                # device      r/s    w/s   kr/s   kw/s wait actv  svc_t  %w  %b
                # ramdisk1    0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd0         0.0    0.0    0.0    0.0  0.0  0.0    0.0   0   0
                # sd1         0.0  139.0    0.0 1850.6  0.0  0.0    0.1   0   1

                # discard the first half of the display (stats since boot)
                lines = [l for l in iostat if len(l) > 0]
                lines = lines[len(lines)/2:]

                assert "extended device statistics" in lines[0]
                headers = lines[1].split()
                assert "device" in headers
                for l in lines[2:]:
                    cols = l.split()
                    # cols[0] is the device
                    # cols[1:] are the values
                    io[cols[0]] = {}
                    for i in range(1, len(cols)):
                        io[cols[0]][self.xlate(headers[i], "sunos")] = cols[i]

            elif Platform.is_freebsd():
                output, _, _ = get_subprocess_output(["iostat", "-x", "-d", "1", "2"], self.log)
                iostat = output.splitlines()

                # Be careful!
                # It looks like SunOS, but some columms (wait, svc_t) have different meaning
                #                        extended device statistics
                # device     r/s   w/s    kr/s    kw/s wait svc_t  %b
                # ad0        3.1   1.3    49.9    18.8    0   0.7   0
                #                         extended device statistics
                # device     r/s   w/s    kr/s    kw/s wait svc_t  %b
                # ad0        0.0   2.0     0.0    31.8    0   0.2   0

                # discard the first half of the display (stats since boot)
                lines = [l for l in iostat if len(l) > 0]
                lines = lines[len(lines)/2:]

                assert "extended device statistics" in lines[0]
                headers = lines[1].split()
                assert "device" in headers
                for l in lines[2:]:
                    cols = l.split()
                    # cols[0] is the device
                    # cols[1:] are the values
                    io[cols[0]] = {}
                    for i in range(1, len(cols)):
                        io[cols[0]][self.xlate(headers[i], "freebsd")] = cols[i]
            else:
                return False

            # If we filter devices, do it know.
            device_blacklist_re = config.get('device_blacklist_re', None)
            if device_blacklist_re:
                filtered_io = {}
                for device, stats in io.iteritems():
                    if not device_blacklist_re.match(device):
                        filtered_io[device] = stats
                        #self.gauge(stats[0], stats[1], tags=["device:{}".format(device)])
            else:
                filtered_io = io

            gauge_to_collect = [
                    "avg_q_sz", "avg_rq_sz",
                    "await", "r_await", "rkb_s",
                    "svctm", "util", "w_await", "wkb_s",
                    ]
            rate_to_collect = [
                    "rrqm_s", "r_s", "wrqm_s", "w_s",
                    ]
            for device_name, metrics in filtered_io.iteritems():
                tags = ["device:{}".format(device_name)]
                for name, value in metrics.iteritems():
                    name = name.replace('%', '').replace('/', '_')
                    if name in rate_to_collect:
                        self.rate("system.io.%s" % name, float(value), tags=tags)
                    if name in gauge_to_collect:
                        self.gauge("system.io.%s" % name, float(value), tags=tags)

        except Exception:
            self.log.exception("Cannot extract IO statistics")
            return False
