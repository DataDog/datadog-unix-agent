import mock
from collections import namedtuple
from agentcheck_mock import AgentCheckTest


@mock.patch("checks.AgentCheck", new_callable=lambda: AgentCheckTest)
@mock.patch("psutil.cpu_times")
@mock.patch("psutil.cpu_count", return_value=2)
def test_cpu_first_run(cpu_count, cpu_times, agent_check):
    from checks.corechecks.system import cpu

    # fake cputimes from psutil
    cputimes = namedtuple("cputimes",
            ["user", "nice", "system", "idle", "iowait",
             "irq", "softirq", "steal", "guest", "guest_nice"])

    cpu_times.return_value = cputimes(user=16683.71,
            nice=6.04,
            system=11054.24,
            idle=729913.18,
            iowait=274.21,
            irq=0.0,
            softirq=104.31,
            steal=0.0,
            guest=0.0,
            guest_nice=0.0)

    c = cpu.Cpu("cpu", {}, {})
    c.check({})
    assert c.get_metrics() == {}

    cpu_times.return_value = cputimes(user=16683.74,
            nice=6.25,
            system=11054.34,
            idle=729921.64,
            iowait=274.21,
            irq=0.1,
            softirq=104.51,
            steal=0.0,
            guest=0.0,
            guest_nice=0.0)

    c.check({})
    assert c.get_metrics() == {
        'system.cpu.system': [{'tags': None, 'type': 'gauge', 'value': 0.2}],
        'system.cpu.user': [{'tags': None, 'type': 'gauge', 'value': 0.12}],
        'system.cpu.wait': [{'tags': None, 'type': 'gauge', 'value': 0.0}],
        'system.cpu.idle': [{'tags': None, 'type': 'gauge', 'value': 4.2300}],
        'system.cpu.stolen': [{'tags': None, 'type': 'gauge', 'value': 0.0}],
        'system.cpu.guest': [{'tags': None, 'type': 'gauge', 'value': 0.0}],
    }
