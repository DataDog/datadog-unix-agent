# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

# stdlib
from collections import namedtuple, defaultdict
import time
import re

# 3p
import paramiko

# project
from utils.strings import skip_blank_lines
from checks import AgentCheck
from aggregator import MetricTypes

SYSTEMS = ['HMC', 'LPAR', 'POOL', 'PROCPOOL', 'MEMPOOL', 'SYS']
DISABLED = ['HMC']


class ManagedServer(object):
    ##
    def __init__(self, name, model, serial):
        self._name = name
        self._model = model
        self._serial = serial
        self._sample_rate = None
        self._last_tm = {}  # local-time
        self._last_sample_ts = {}  # hmc-time
        for sys in SYSTEMS:
            self._last_tm[sys] = None
            self._last_sample_ts[sys] = None

    @property
    def name(self):
        return self._name

    @property
    def sample_rate(self):
        return self._sample_rate

    @sample_rate.setter
    def sample_rate(self, sample_rate):
        self._sample_rate = sample_rate

    def get_last_tm(self, subsys):
        return self._last_tm[subsys]

    def get_last_sample_ts(self, subsys):
        return self._last_sample_ts[subsys]

    def set_last_tm(self, subsys, tm):
        self._last_tm[subsys] = tm

    def set_last_sample_ts(self, subsys, ts):
        self._last_sample_ts[subsys] = ts


class HMC(AgentCheck):
    HMC_SERVICE_CHECK_NAME = 'hmc.can_connect'
    OPTIONS = [
        ('host', True, None, str),
        ('port', False, 22, int),
        ('username', True, None, str),
        ('password', False, None, str),
        ('private_key_file', False, None, str),
        ('private_key_type', False, 'rsa', str),
        ('add_missing_keys', False, False, bool),
    ]

    Config = namedtuple('Config', [
        'host',
        'port',
        'username',
        'password',
        'private_key_file',
        'private_key_type',
        'add_missing_keys',
    ])

    # HMC environments
    HMC_LSLPARUTIL_ENV = {
        'LC_ALL': 'en_US',
        'LANG': 'en_US',
        'LC_NUMERIC': 'en_US'
    }

    # HMC sample time format: 02/23/2006 12:00:01
    HMC_SAMPLE_TIME_FORMAT = '%m/%d/%Y %H:%M:%S'

    # HMC monitoring commands
    HMC_GET_VERSION = 'lshmc -v'
    HMC_GET_SERVERS = 'lssyscfg -r sys -F name,type_model,serial_num'
    HMC_ID_NAME_TRANSLATE = 'lssyscfg -r lpar -m {name} -F lpar_id,name'
    HMC_GET_LPAR_SAMPLE_RATE = 'lslparutil -r config -m {name} -F sample_rate'

    HMC_LPAR_STATS_TEMPLATE = 'lslparutil -r {subsys} --startyear {year} --startmonth {month} --startday {day} '\
        '--starthour {hour} --startminute {minute} -m {name} -F time,{fields} --filter \"event_types=sample\"'
    HMC_LPAR_STATS_FIELDS = {
        'HMC': [],
        'LPAR': [
            ('lpar_name', None),
            ('curr_proc_units', MetricTypes.GAUGE),
            ('curr_procs', MetricTypes.GAUGE),
            ('curr_sharing_mode', None),
            ('entitled_cycles', MetricTypes.GAUGE),
            ('capped_cycles', MetricTypes.GAUGE),
            ('uncapped_cycles', MetricTypes.GAUGE),
        ],
        'POOL': [
            ('total_pool_cycles', MetricTypes.GAUGE),
            ('utilized_pool_cycles', MetricTypes.GAUGE),
            ('configurable_pool_proc_units', MetricTypes.GAUGE),
            ('borrowed_pool_proc_units', MetricTypes.GAUGE),
            ('curr_avail_pool_proc_units', MetricTypes.GAUGE),
        ],
        'PROCPOOL': [
            ('shared_proc_pool_id', MetricTypes.GAUGE),
            ('total_pool_cycles', MetricTypes.GAUGE),
            ('utilized_pool_cycles', MetricTypes.GAUGE),
        ],
        'MEMPOOL': [
            ('curr_pool_mem', MetricTypes.GAUGE),
            ('lpar_curr_io_entitled_mem', MetricTypes.GAUGE),
            ('lpar_mapped_io_entitled_mem', MetricTypes.GAUGE),
            ('lpar_run_mem', MetricTypes.GAUGE),
            ('sys_firmware_pool_mem', MetricTypes.GAUGE),
        ],
        'SYS': [
            ('curr_avail_sys_mem', MetricTypes.GAUGE),
            ('configurable_sys_mem', MetricTypes.GAUGE),
            ('sys_firmware_mem', MetricTypes.GAUGE),
        ],
    }

    # dictionary of tuples: key is subsys; tuple is (hmc compatibility,
    HMC_LPAR_STATS_EXTRA_FIELDS = {
        'LPAR': [
            (700, [
                ('shared_cycles_while_active', MetricTypes.GAUGE),
            ]),
            (734, [
                ('mem_mode', None),
                ('curr_mem', MetricTypes.GAUGE),
                ('phys_run_mem', MetricTypes.GAUGE),
                ('curr_io_entitled_mem', MetricTypes.GAUGE),
                ('mapped_io_entitled_mem', MetricTypes.GAUGE),
                ('mem_overage_cooperation', MetricTypes.GAUGE),
            ]),
            (772, [
                ('idle_cycles', MetricTypes.GAUGE),
            ]),
        ],
    }

    # CoD
    HMC_LPAR_STATS_COD = 'lslparutil -r all -n 2 -m {name} ' \
        '-F time,used_proc_min,unreported_proc_min --filter \"event_types=utility_cod_proc_usage\"'

    # HMC internal monitoring commands
    HMC_LS_CMD = 'lshmc -V'
    HMC_MEMINFO_CMD = 'cat /proc/meminfo'
    HMC_MON_CMD = 'monhmc -r swap -n 0'
    HMC_PROCSTAT_CMD = 'cat /proc/stat'

    def __init__(self, name, init_config, instance, aggregator=None):
        AgentCheck.__init__(self, name, init_config, instance, aggregator)

        self._hmc_versions = {}
        self._last_refresh = {}
        self._managed_servers = defaultdict(dict)  # key server name, value property dict

    def _load_conf(self, instance):
        params = []
        for option, required, default, expected_type in self.OPTIONS:
            value = instance.get(option)
            if required and (not value or type(value) != expected_type):
                raise Exception("Please specify a valid {0}".format(option))

            if value is None or type(value) != expected_type:
                self.log.debug("Bad or missing value for {0} parameter. Using default".format(option))
                value = default

            params.append(value)

        return self.Config._make(params)

    def check(self, instance):
        conf = self._load_conf(instance)
        tags = instance.get('tags', [])
        tags.append("hmc-instance:{0}-{1}".format(conf.host, conf.port))

        private_key = None

        if conf.private_key_file is not None:
            try:
                if conf.private_key_type == 'ecdsa':
                    private_key = paramiko.ECDSAKey.from_private_key_file(conf.private_key_file)
                else:
                    private_key = paramiko.RSAKey.from_private_key_file(conf.private_key_file)
            except IOError:
                self.warning("Unable to find private key file: {}".format(conf.private_key_file))
            except paramiko.ssh_exception.PasswordRequiredException:
                self.warning("Private key file is encrypted but no password was given")
            except paramiko.ssh_exception.SSHException:
                self.warning("Private key file is invalid")

        client = paramiko.SSHClient()
        if conf.add_missing_keys:
            client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.load_system_host_keys()

        exception_message = "No errors occured"
        try:
            # Try to connect to check status of SSH
            try:
                client.connect(
                    conf.host, port=conf.port, username=conf.username,
                    password=conf.password, pkey=private_key
                )
                self.service_check(
                    self.HMC_SERVICE_CHECK_NAME, AgentCheck.OK, tags=tags, message=exception_message
                )
            except Exception as e:
                exception_message = str(e)
                status = AgentCheck.CRITICAL
                self.service_check(
                    self.HMC_SERVICE_CHECK_NAME, status, tags=tags, message=exception_message
                )

                raise

            custom = instance.get('custom')
            if custom:
                self.hmc_run_custom(client, cmd=custom)
                return

            if conf not in self._hmc_versions:
                version = self.hmc_get_version(client, environment=self.HMC_LSLPARUTIL_ENV)
                self._hmc_versions[conf] = version

            if conf not in self._last_refresh or (time.time() - self._last_refresh[conf]) > self._refresh_period:
                servers = self.hmc_get_managed_servers(client, environment=self.HMC_LSLPARUTIL_ENV)
                for server in servers:
                    if server not in self._managed_servers:
                        self._managed_servers[server] = ManagedServer(server[0], server[1], server[2])

                for server in self._managed_servers:
                    if server not in servers:
                        # server no longer managed
                        del self._managed_servers[server]

                self._last_refresh[conf] = time.time()

            for _, server in self._managed_servers.iteritems():
                if not server.sample_rate:
                    try:
                        sample_rate = self.hmc_get_sample_rate(client, server, environment=self.HMC_LSLPARUTIL_ENV)
                        server.sample_rate = sample_rate
                    except ValueError:
                        self.log.error('Unable to collect sample rate for {}'.format(server.name))
                        continue

                tags = ['server:{name}'.format(name=server.name)]
                for subsys in SYSTEMS:
                    self.hmc_sample(
                        client,
                        version,
                        subsys,
                        server,
                        tags=tags,
                        environment=self.HMC_LSLPARUTIL_ENV
                    )

            env = {'LANG': 'C'}
            self.hmc_ls(client, environment=env)
            self.hmc_meminfo(client, environment=env)
            self.hmc_monhmc_swap(client, environment=env)
            self.hmc_procstat(client, environment=env)

        finally:
            # Always close the client, failure to do so leaks one thread per connection left open
            client.close()

    def hmc_run_custom(self, ssh_client, cmd, environment={}):
        # this will not submit any metrics and is only for debugging purposes
        try:
            _, stdout, stderr = ssh_client.exec_command(cmd, environment=environment)

            self.log.debug("command %s STDOUT: %s", stdout.read())
            self.log.debug("command %s STDERR: %s", stderr.read())
        except Exception:
            raise

    def hmc_get_version(self, ssh_client, environment={}):
        # "lshmc -v" 2>/dev/null|egrep "RM |DS "|tail -2`;
        try:
            _, stdout, _ = ssh_client.exec_command(self.HMC_GET_VERSION, environment=environment)
        except Exception:
            raise

        lines = [l for l in stdout.read().splitlines() if re.search('DS |RM ', l)]
        if not lines:
            return None

        lines = lines[1:]
        version = lines[-1].split()[1].replace('.', '')
        version = version.replace('V', '')
        version = version.replace('R', '')

        # TODO: no magic numbers
        if len(version) < 3:
            return 700

        return int(version[0:3])

    def hmc_get_managed_servers(self, ssh_client, environment={}):
        try:
            _, stdout, _ = ssh_client.exec_command(self.HMC_GET_SERVERS, environment=environment)
        except Exception:
            raise

        servers = []
        for line in stdout.read().splitlines():
            server = line.split(',')
            servers.append(tuple(server))

        return servers

    def hmc_get_sample_rate(self, ssh_client, server, environment={}):
        try:
            command = self.HMC_GET_LPAR_SAMPLE_RATE.format(name=server.name)
            _, stdout, _ = ssh_client.exec_command(command, environment=environment)
        except Exception:
            raise

        try:
            output = stdout.read()
            sample_rate = int(output)
        except ValueError:
            self.log.error("unable to collect sample rate for {}: {}".format(server.name, output))
            raise

        return sample_rate

    def hmc_sample(self, ssh_client, hmc_version, subsys, server, environment={}, tags=[]):
        if subsys in DISABLED:
            self.log.debug('subsystem %s disabled - skipping', subsys)
            return

        last_tm = server.get_last_tm(subsys)
        if last_tm:
            elapsed = (time.time() - last_tm)
            if elapsed < server.sample_rate:
                self.log.info('skipping HMC sampling, not enough time has passed for new samples')
                return
        else:
            # TODO: this might not be aligned with the HMC server time - grab it from there.
            last_tm = time.localtime(time.time())

        fields = self.HMC_LPAR_STATS_FIELDS[subsys]
        extra_fields = self.HMC_LPAR_STATS_EXTRA_FIELDS.get(subsys, {})
        for version, extras in extra_fields:
            if version <= hmc_version:
                fields.extend(extras)

        try:
            command = self.HMC_LPAR_STATS_TEMPLATE.format(
                subsys=subsys.lower(),
                year=last_tm.tm_year,
                month=last_tm.tm_mon,
                day=last_tm.tm_mday,
                hour=last_tm.tm_hour,
                minute=last_tm.tm_min,
                name=server.name,
                fields=','.join([f[0] for f in fields])
            )
            _, stdout, _ = ssh_client.exec_command(command, environment=environment)
        except Exception:
            raise

        samples = []
        lines = stdout.read().splitlines()
        for line in lines:
            sample = line.split(',')
            if len(fields) != len(sample[1:]):
                self.log.debug('sample length mismatch, skipping...')
                continue

            sample[0] = time.strptime(sample[0], self.HMC_SAMPLE_TIME_FORMAT)
            if not last_tm or sample[0] > last_tm:
                samples.append(sample)

        if not samples:
            self.log.debug("no samples were collected")
            return

        # newest sample available
        last_sample_ts = samples[0][0]

        # update timestemps
        server.set_last_tm(subsys, time.time())
        server.set_last_sample_ts(subsys, last_sample_ts)

        # traverse old to new
        for sample in reversed(samples):
            # get tags
            sample_tags = tags
            for i, field in enumerate(fields):
                if field[1] is None:
                    sample_tags.append("{field}:{value}".format(field=field[0], value=sample[i+1]))

            # submit metrics
            for i, field in enumerate(fields):
                if field[1] is None:
                    continue
                try:
                    if field[1] == MetricTypes.GAUGE:
                        # NOTE: unsure about using the timestamp like this
                        self.gauge('hmc.{sys}.{field}'.format(sys=subsys, field=field[0]),
                                float(sample[i+1]),
                                timestamp=time.mktime(sample[0]),
                                tags=sample_tags)
                    else:
                        pass
                except ValueError:
                    self.log.exception("unable to submit metric for {}".format(field))

    def hmc_ls(self, ssh_client, environment={}):
        try:
            ssh_client.exec_command(self.HMC_LS_CMD, environment=environment)
        except Exception:
            pass

    def hmc_meminfo(self, ssh_client, environment={}, tags=[]):
        try:
            # Sample output
            #
            # cat /proc/meminfo #example
            # MemTotal:      4128368 kB
            # MemFree:        161392 kB
            # Buffers:        397776 kB
            #
            # Cached:        1457064 kB
            _, stdout, _  = ssh_client.exec_command(self.HMC_MEMINFO_CMD, environment=environment)
        except Exception:
            raise

        for line in skip_blank_lines(stdout.read().splitlines()):
            m = line.split()
            metric = m[0][:-1]
            self.gauge('hmc.system.memory.{metric}'.format(metric=metric), float(m[1]), tags=tags)

    def hmc_monhmc_swap(self, ssh_client, environment={}, tags=[]):
        try:
            # Sample output
            #
            # Swap: 2040244k total, 266000k used, 1774244k free, 2282460k cached

            _, stdout, _  = ssh_client.exec_command(self.HMC_MON_CMD, environment=environment)
        except Exception:
            raise

        swap = stdout.read()
        swap = ' '.join(swap.split()[1:])
        swap = swap.split(',')
        for stat in swap:
            val, metric = stat.split()
            val = re.sub("\D", "", val)
            self.gauge('hmc.system.memory.swap.{metric}'.format(metric=metric), float(val), tags=tags)

    def hmc_procstat(self, ssh_client, environment={}):
        try:
            ssh_client.exec_command(self.HMC_PROCSTAT_CMD, environment=environment)
        except Exception:
            pass
