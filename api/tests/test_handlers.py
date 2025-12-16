# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2025 Datadog, Inc.

from datetime import datetime
import pytest
from api.handlers import AgentStatusHandler


def process_agent_info(agent_info, check_stats=None):
    """Helper function to test process_agent_info without Tornado initialization."""
    # Create a mock handler instance
    class MockHandler:
        def process_agent_info(self, info, check_stats=None):
            return AgentStatusHandler.process_agent_info(self, info, check_stats)

    handler = MockHandler()
    return handler.process_agent_info(agent_info, check_stats)


class TestProcessAgentInfo:
    """Tests for AgentStatusHandler.process_agent_info method."""

    def test_process_agent_info_with_metrics_only(self):
        """Test processing check that only submits metrics."""
        check_name = "test_check"
        signature_hash = 12345

        agent_info = {
            'sources': {
                (check_name, signature_hash): 42  # 42 metric samples
            }
        }

        check_stats = {
            signature_hash: {
                'config_source': '/etc/datadog/conf.d/test.yaml',
                'instance_index': 0,
                'execution_times': [10.5, 11.2, 9.8],
                'total_runs': 3,
                'last_execution': datetime(2025, 12, 16, 10, 30, 45, 123000)
            }
        }

        result = process_agent_info(agent_info, check_stats)

        assert 'checks' in result
        assert len(result['checks']) == 1

        instance_id = f"{check_name}:{format(signature_hash, 'x')}"
        assert instance_id in result['checks']

        check_data = result['checks'][instance_id]
        assert check_data['check_name'] == check_name
        assert check_data['signature_hash'] == signature_hash
        assert check_data['config_source'] == '/etc/datadog/conf.d/test.yaml'
        assert check_data['instance_index'] == 0
        assert check_data['metrics'] == 42
        assert check_data['service_checks'] == 0
        assert check_data['events'] == 0
        assert check_data['total_runs'] == 3
        assert check_data['avg_execution_time_ms'] == 10.0  # round((10.5 + 11.2 + 9.8) / 3, 0)
        assert '2025-12-16 10:30:45.123 UTC' in check_data['last_execution']

    def test_process_agent_info_with_service_checks_only(self):
        """Test processing check that only submits service checks (no metrics)."""
        check_name = "service_check_only"
        signature_hash = 67890

        agent_info = {
            'sources': {},  # No metrics
            'service_check_sources': {
                (check_name, signature_hash): 5  # 5 service checks
            }
        }

        check_stats = {
            signature_hash: {
                'config_source': '/etc/datadog/conf.d/service.yaml',
                'instance_index': 1,
                'execution_times': [5.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 11, 0, 0, 0)
            }
        }

        result = process_agent_info(agent_info, check_stats)

        assert 'checks' in result
        assert len(result['checks']) == 1

        instance_id = f"{check_name}:{format(signature_hash, 'x')}"
        check_data = result['checks'][instance_id]

        assert check_data['check_name'] == check_name
        assert check_data['metrics'] == 0
        assert check_data['service_checks'] == 5
        assert check_data['events'] == 0
        assert check_data['config_source'] == '/etc/datadog/conf.d/service.yaml'
        assert check_data['instance_index'] == 1

    def test_process_agent_info_with_events_only(self):
        """Test processing check that only submits events."""
        check_name = "event_check"
        signature_hash = 11111

        agent_info = {
            'sources': {},  # No metrics
            'service_check_sources': {},  # No service checks
            'event_sources': {
                (check_name, signature_hash): 3  # 3 events
            }
        }

        check_stats = {
            signature_hash: {
                'config_source': '/etc/datadog/conf.d/events.yaml',
                'instance_index': 0,
                'execution_times': [20.0, 25.0],
                'total_runs': 2,
                'last_execution': datetime(2025, 12, 16, 12, 0, 0, 0)
            }
        }

        result = process_agent_info(agent_info, check_stats)

        instance_id = f"{check_name}:{format(signature_hash, 'x')}"
        check_data = result['checks'][instance_id]

        assert check_data['metrics'] == 0
        assert check_data['service_checks'] == 0
        assert check_data['events'] == 3
        assert check_data['total_runs'] == 2
        assert check_data['avg_execution_time_ms'] == 22.0  # round((20 + 25) / 2, 0)

    def test_process_agent_info_with_all_types(self):
        """Test processing check that submits metrics, service checks, and events."""
        check_name = "full_check"
        signature_hash = 99999

        agent_info = {
            'sources': {
                (check_name, signature_hash): 100  # 100 metrics
            },
            'service_check_sources': {
                (check_name, signature_hash): 2  # 2 service checks
            },
            'event_sources': {
                (check_name, signature_hash): 1  # 1 event
            }
        }

        check_stats = {
            signature_hash: {
                'config_source': '/etc/datadog/conf.d/full.yaml',
                'instance_index': 0,
                'execution_times': [15.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 13, 0, 0, 0)
            }
        }

        result = process_agent_info(agent_info, check_stats)

        instance_id = f"{check_name}:{format(signature_hash, 'x')}"
        check_data = result['checks'][instance_id]

        assert check_data['metrics'] == 100
        assert check_data['service_checks'] == 2
        assert check_data['events'] == 1

    def test_process_agent_info_multiple_instances(self):
        """Test that multiple instances of same check are tracked separately."""
        check_name = "multi_instance"
        sig_hash_1 = 1111
        sig_hash_2 = 2222
        sig_hash_3 = 3333

        agent_info = {
            'sources': {
                (check_name, sig_hash_1): 10,
                (check_name, sig_hash_2): 20,
                (check_name, sig_hash_3): 30,
            }
        }

        check_stats = {
            sig_hash_1: {
                'config_source': '/etc/datadog/conf.d/multi.yaml',
                'instance_index': 0,
                'execution_times': [5.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 10, 0, 0, 0)
            },
            sig_hash_2: {
                'config_source': '/etc/datadog/conf.d/multi.yaml',
                'instance_index': 1,
                'execution_times': [10.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 10, 0, 1, 0)
            },
            sig_hash_3: {
                'config_source': '/etc/datadog/conf.d/multi.yaml',
                'instance_index': 2,
                'execution_times': [15.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 10, 0, 2, 0)
            }
        }

        result = process_agent_info(agent_info, check_stats)

        assert len(result['checks']) == 3

        instance_id_1 = f"{check_name}:{format(sig_hash_1, 'x')}"
        instance_id_2 = f"{check_name}:{format(sig_hash_2, 'x')}"
        instance_id_3 = f"{check_name}:{format(sig_hash_3, 'x')}"

        assert result['checks'][instance_id_1]['metrics'] == 10
        assert result['checks'][instance_id_1]['instance_index'] == 0

        assert result['checks'][instance_id_2]['metrics'] == 20
        assert result['checks'][instance_id_2]['instance_index'] == 1

        assert result['checks'][instance_id_3]['metrics'] == 30
        assert result['checks'][instance_id_3]['instance_index'] == 2

    def test_process_agent_info_without_check_stats(self):
        """Test processing when check_stats is not provided."""
        check_name = "no_stats"
        signature_hash = 55555

        agent_info = {
            'sources': {
                (check_name, signature_hash): 50
            }
        }

        # No check_stats provided (or None)
        result = process_agent_info(agent_info, check_stats=None)

        instance_id = f"{check_name}:{format(signature_hash, 'x')}"
        check_data = result['checks'][instance_id]

        # Should use defaults when stats not available
        assert check_data['config_source'] == 'unknown'
        assert check_data['instance_index'] == 0
        assert check_data['avg_execution_time_ms'] == 0
        assert check_data['total_runs'] == 0
        assert check_data['last_execution'] == 'Never'

    def test_process_agent_info_empty_execution_times(self):
        """Test handling of empty execution_times list."""
        check_name = "empty_times"
        signature_hash = 77777

        agent_info = {
            'sources': {
                (check_name, signature_hash): 5
            }
        }

        check_stats = {
            signature_hash: {
                'config_source': '/test/config.yaml',
                'instance_index': 0,
                'execution_times': [],  # Empty list
                'total_runs': 0,
                'last_execution': None
            }
        }

        result = process_agent_info(agent_info, check_stats)

        instance_id = f"{check_name}:{format(signature_hash, 'x')}"
        check_data = result['checks'][instance_id]

        # Should handle empty list gracefully
        assert check_data['avg_execution_time_ms'] == 0
        assert check_data['last_execution'] == 'Never'

    def test_process_agent_info_different_checks(self):
        """Test processing multiple different checks."""
        agent_info = {
            'sources': {
                ('cpu', 1001): 45,
                ('memory', 1002): 30,
                ('disk', 1003): 60,
            },
            'service_check_sources': {
                ('cpu', 1001): 1,
                ('disk', 1003): 1,
            }
        }

        check_stats = {
            1001: {
                'config_source': '/etc/datadog/conf.d/cpu.yaml',
                'instance_index': 0,
                'execution_times': [23.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 14, 0, 0, 0)
            },
            1002: {
                'config_source': '/etc/datadog/conf.d/memory.yaml',
                'instance_index': 0,
                'execution_times': [10.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 14, 0, 1, 0)
            },
            1003: {
                'config_source': '/etc/datadog/conf.d/disk.yaml',
                'instance_index': 0,
                'execution_times': [35.0],
                'total_runs': 1,
                'last_execution': datetime(2025, 12, 16, 14, 0, 2, 0)
            }
        }

        result = process_agent_info(agent_info, check_stats)

        assert len(result['checks']) == 3

        cpu_id = f"cpu:{format(1001, 'x')}"
        memory_id = f"memory:{format(1002, 'x')}"
        disk_id = f"disk:{format(1003, 'x')}"

        assert result['checks'][cpu_id]['check_name'] == 'cpu'
        assert result['checks'][cpu_id]['metrics'] == 45
        assert result['checks'][cpu_id]['service_checks'] == 1

        assert result['checks'][memory_id]['check_name'] == 'memory'
        assert result['checks'][memory_id]['metrics'] == 30
        assert result['checks'][memory_id]['service_checks'] == 0

        assert result['checks'][disk_id]['check_name'] == 'disk'
        assert result['checks'][disk_id]['metrics'] == 60
        assert result['checks'][disk_id]['service_checks'] == 1
