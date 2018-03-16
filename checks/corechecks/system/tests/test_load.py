# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock
from agentcheck_mock import AgentCheckTest


@mock.patch("checks.AgentCheck", new_callable=lambda: AgentCheckTest)
@mock.patch("psutil.cpu_count", return_value=2)
@mock.patch("os.getloadavg", return_value=(0.42, 0.43, 0.49))
def test_load(getloadavg, cpu_count, agent_check):
    from checks.corechecks.system import load

    c = load.Load("load", {}, {})
    c.check({})
    assert c.get_metrics() == {
        'system.load.1': [{'tags': None, 'type': 'gauge', 'value': 0.42}],
        'system.load.5': [{'tags': None, 'type': 'gauge', 'value': 0.43}],
        'system.load.15': [{'tags': None, 'type': 'gauge', 'value': 0.49}],
        'system.load.norm.1': [{'tags': None, 'type': 'gauge', 'value': 0.21}],
        'system.load.norm.5': [{'tags': None, 'type': 'gauge', 'value': 0.215}],
        'system.load.norm.15': [{'tags': None, 'type': 'gauge', 'value': 0.245}],
    }

@mock.patch("checks.AgentCheck", new_callable=lambda: AgentCheckTest)
@mock.patch("psutil.cpu_count", return_value=0)
@mock.patch("os.getloadavg", return_value=(0.42, 0.43, 0.49))
def test_load_no_cpu_count(getloadavg, cpu_count, agent_check):
    from checks.corechecks.system import load

    c = load.Load("load", {}, {})
    try:
        c.check({})
        assert 0, "load check should have raise an error"
    except Exception as e:
        assert str(e) == "Cannot determine number of cores"

    assert c.get_metrics() == {
        'system.load.1': [{'tags': None, 'type': 'gauge', 'value': 0.42}],
        'system.load.5': [{'tags': None, 'type': 'gauge', 'value': 0.43}],
        'system.load.15': [{'tags': None, 'type': 'gauge', 'value': 0.49}],
    }
