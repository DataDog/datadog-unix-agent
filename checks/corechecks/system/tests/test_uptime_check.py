import mock
from agentcheck_mock import AgentCheckTest


@mock.patch("checks.AgentCheck", new_callable=lambda: AgentCheckTest)
@mock.patch("uptime.uptime", return_value=21)
def test_uptime_check(uptime, agent_check_test):
    from checks.corechecks.system import uptime_check

    u = uptime_check.UptimeCheck("uptime", {}, {})
    u.check({})
    assert u.get_metrics() == {
        "system.uptime": [{"type": "gauge", "value": 21, "tags": None}]
    }
