import mock
from collections import namedtuple

from agentcheck_mock import AgentCheckTest


@mock.patch("checks.AgentCheck", new_callable=lambda: AgentCheckTest)
@mock.patch("psutil.virtual_memory")
@mock.patch("psutil.swap_memory")
def test_memory_linux(swap_memory, virtual_memory, agent_check):
    from checks.corechecks.system import memory

    svmem = namedtuple("svmem", ["total", "available", "percent", "used",
        "free", "active", "inactive", "buffers", "cached", "shared"])
    sswap = namedtuple("sswap", ["total", "used", "free", "percent", "sin", "sout"])

    virtual_memory.return_value = svmem(total=9177399296,
        available=5566582784,
        percent=39.3,
        used=2958319616,
        free=4841459712,
        active=1700761600,
        inactive=1062944768,
        buffers=68628480,
        cached=1308991488,
        shared=500330496)
    swap_memory.return_value = sswap(
        total=10485755904,
        used=1024,
        free=10485754880,
        percent=1.0,
        sin=0,
        sout=0)

    c = memory.Memory("memory", {}, {})
    c.check({})
    assert c.get_metrics() == {
        'system.mem.total': [{'tags': None, 'type': 'gauge', 'value': 8752}],
        'system.mem.free': [{'tags': None, 'type': 'gauge', 'value': 4617}],
        'system.mem.used': [{'tags': None, 'type': 'gauge', 'value': 4135}],
        'system.mem.usable': [{'tags': None, 'type': 'gauge', 'value': 5308}],
        'system.mem.pct_usable': [{'tags': None, 'type': 'gauge', 'value': 0}],
        'system.swap.total': [{'tags': None, 'type': 'gauge', 'value': 9999}],
        'system.swap.free': [{'tags': None, 'type': 'gauge', 'value': 9999}],
        'system.swap.used': [{'tags': None, 'type': 'gauge', 'value': 0}],
        'system.swap.pct_free': [{'tags': None, 'type': 'gauge', 'value': 1}],
    }
