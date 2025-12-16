# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2025 Datadog, Inc.

import time
from datetime import datetime
from collector.collector import Collector
from checks import AgentCheck
from aggregator import MetricsAggregator


class StatsTestCheck(AgentCheck):
    """A minimal check for testing execution stats tracking."""
    DEFAULT_MIN_COLLECTION_INTERVAL = 0  # Allow running as fast as possible

    def __init__(self, name, init_config, instance, aggregator):
        super(StatsTestCheck, self).__init__(name, init_config, instance, aggregator)
        self.run_count = 0
        self.sleep_time = instance.get('sleep_time', 0)

    def check(self, instance):
        """Execute check - optionally sleep to simulate work."""
        self.run_count += 1
        if self.sleep_time > 0:
            time.sleep(self.sleep_time)

        # Submit a metric so the check shows up
        self.gauge('test.metric', 1.0)
        return None


class StatsTestConfig:
    """Mock config for execution stats testing."""

    def __init__(self, instances_config):
        self._instances = instances_config

    def __getitem__(self, key):
        if key == "additional_checksd":
            return "/dev/null"
        raise KeyError(key)

    def get(self, key, default=None):
        if key == "min_collection_interval":
            return 0  # Allow checks to run as fast as possible for testing
        return default

    def get_check_configs(self):
        return self._instances


class TestCollectorExecutionStats:
    """Tests for collector execution statistics tracking."""

    def test_execution_stats_tracked(self):
        """Test that execution_times, total_runs, and last_execution are tracked."""
        config = StatsTestConfig({
            "test_source": {
                "stats_test": [
                    {
                        "init_config": {},
                        "instances": [{"name": "instance1"}],
                        "_config_source": "/test/config.yaml",
                        "_instance_index": 0
                    }
                ]
            }
        })

        aggregator = MetricsAggregator('test-host')
        collector = Collector(config, aggregator)
        collector.set_loaders = lambda: None
        collector._check_classes = {"stats_test": StatsTestCheck}

        # Instantiate checks
        collector.instantiate_checks()

        # Verify check_stats initialized
        assert len(collector._check_stats) == 1
        signature_hash = list(collector._check_stats.keys())[0]
        stats = collector._check_stats[signature_hash]

        assert stats['config_source'] == '/test/config.yaml'
        assert stats['instance_index'] == 0
        assert stats['execution_times'] == []
        assert stats['total_runs'] == 0
        assert stats['last_execution'] is None

        # Run checks once
        before_run = datetime.utcnow()
        collector.run_checks()
        after_run = datetime.utcnow()

        # Verify stats updated
        stats = collector._check_stats[signature_hash]
        assert len(stats['execution_times']) == 1
        assert stats['execution_times'][0] >= 0  # execution time in ms
        assert stats['total_runs'] == 1
        assert stats['last_execution'] is not None
        assert before_run <= stats['last_execution'] <= after_run

        # Run checks again (reset _last_run_time to simulate time passing)
        for check in collector._check_instances['stats_test']:
            check._last_run_time = 0
        collector.run_checks()

        # Verify stats accumulated
        stats = collector._check_stats[signature_hash]
        assert len(stats['execution_times']) == 2
        assert stats['total_runs'] == 2

    def test_execution_times_capped_at_100(self):
        """Test that execution times list is capped at 100 entries."""
        config = StatsTestConfig({
            "test_source": {
                "stats_test": [
                    {
                        "init_config": {},
                        "instances": [{"name": "instance1"}],
                        "_config_source": "/test/config.yaml",
                        "_instance_index": 0
                    }
                ]
            }
        })

        aggregator = MetricsAggregator('test-host')
        collector = Collector(config, aggregator)
        collector.set_loaders = lambda: None
        collector._check_classes = {"stats_test": StatsTestCheck}

        collector.instantiate_checks()
        signature_hash = list(collector._check_stats.keys())[0]

        # Run checks 150 times (reset _last_run_time each time to bypass interval)
        for i in range(150):
            for check in collector._check_instances['stats_test']:
                check._last_run_time = 0
            collector.run_checks()

        # Verify only last 100 execution times are kept
        stats = collector._check_stats[signature_hash]
        assert len(stats['execution_times']) == 100
        assert stats['total_runs'] == 150

    def test_check_stats_exposed_in_status(self):
        """Test that check_stats is available in collector.status."""
        config = StatsTestConfig({
            "test_source": {
                "stats_test": [
                    {
                        "init_config": {},
                        "instances": [{"name": "instance1"}],
                        "_config_source": "/test/config.yaml",
                        "_instance_index": 0
                    }
                ]
            }
        })

        aggregator = MetricsAggregator('test-host')
        collector = Collector(config, aggregator)
        collector.set_loaders = lambda: None
        collector._check_classes = {"stats_test": StatsTestCheck}

        collector.instantiate_checks()

        # Verify check_stats set after instantiation
        _, info = collector.status.snapshot()
        assert 'check_stats' in info
        assert len(info['check_stats']) == 1

        # Run checks
        collector.run_checks()

        # Verify check_stats updated after run
        _, info = collector.status.snapshot()
        assert 'check_stats' in info
        signature_hash = list(info['check_stats'].keys())[0]
        stats = info['check_stats'][signature_hash]

        assert stats['total_runs'] == 1
        assert len(stats['execution_times']) == 1
        assert stats['last_execution'] is not None

    def test_multiple_instances_tracked_separately(self):
        """Test that multiple instances of the same check are tracked separately."""
        config = StatsTestConfig({
            "test_source": {
                "stats_test": [
                    {
                        "init_config": {},
                        "instances": [
                            {"name": "instance1"},
                            {"name": "instance2"},
                            {"name": "instance3"}
                        ],
                        "_config_source": "/test/config.yaml",
                        "_instance_index": 0
                    }
                ]
            }
        })

        aggregator = MetricsAggregator('test-host')
        collector = Collector(config, aggregator)
        collector.set_loaders = lambda: None
        collector._check_classes = {"stats_test": StatsTestCheck}

        collector.instantiate_checks()

        # Should have 3 separate stat entries
        assert len(collector._check_stats) == 3

        # Run checks
        collector.run_checks()

        # Each instance should have its own stats
        for signature_hash, stats in collector._check_stats.items():
            assert stats['total_runs'] == 1
            assert len(stats['execution_times']) == 1

    def test_execution_time_accuracy(self):
        """Test that execution time is measured with reasonable accuracy."""
        config = StatsTestConfig({
            "test_source": {
                "stats_test": [
                    {
                        "init_config": {},
                        "instances": [{"name": "slow", "sleep_time": 0.05}],  # 50ms sleep
                        "_config_source": "/test/config.yaml",
                        "_instance_index": 0
                    }
                ]
            }
        })

        aggregator = MetricsAggregator('test-host')
        collector = Collector(config, aggregator)
        collector.set_loaders = lambda: None
        collector._check_classes = {"stats_test": StatsTestCheck}

        collector.instantiate_checks()
        collector.run_checks()

        signature_hash = list(collector._check_stats.keys())[0]
        stats = collector._check_stats[signature_hash]

        # Execution time should be at least 50ms (accounting for overhead, use 45ms threshold)
        assert stats['execution_times'][0] >= 45.0
        # Should be less than 200ms (generous upper bound)
        assert stats['execution_times'][0] < 200.0

    def test_stats_persist_across_runs(self):
        """Test that stats are preserved across multiple check runs."""
        config = StatsTestConfig({
            "test_source": {
                "stats_test": [
                    {
                        "init_config": {},
                        "instances": [{"name": "instance1"}],
                        "_config_source": "/test/config.yaml",
                        "_instance_index": 0
                    }
                ]
            }
        })

        aggregator = MetricsAggregator('test-host')
        collector = Collector(config, aggregator)
        collector.set_loaders = lambda: None
        collector._check_classes = {"stats_test": StatsTestCheck}

        collector.instantiate_checks()

        # Run checks multiple times and track last_execution progression
        last_executions = []
        for i in range(5):
            # Reset _last_run_time to bypass min_collection_interval
            for check in collector._check_instances['stats_test']:
                check._last_run_time = 0
            collector.run_checks()
            signature_hash = list(collector._check_stats.keys())[0]
            last_exec = collector._check_stats[signature_hash]['last_execution']
            last_executions.append(last_exec)
            time.sleep(0.01)  # Small delay to ensure timestamps differ

        # Verify last_execution keeps updating
        for i in range(1, len(last_executions)):
            assert last_executions[i] >= last_executions[i-1]

        # Verify cumulative stats
        signature_hash = list(collector._check_stats.keys())[0]
        stats = collector._check_stats[signature_hash]
        assert stats['total_runs'] == 5
        assert len(stats['execution_times']) == 5

