# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2025 Datadog, Inc.

import pytest
from collector.collector import Collector
from checks import AgentCheck


# ----------------------------------------------------------------------
# Dummy check and config for testing min_collection_interval logic
# ----------------------------------------------------------------------

class DummyCheck(AgentCheck):
    """A minimal AgentCheck subclass with its own default interval."""
    DEFAULT_MIN_COLLECTION_INTERVAL = 10

    def __init__(self, name, init_config, instance, aggregator):
        super(DummyCheck, self).__init__(name, init_config, instance, aggregator)


class DummyConfig:
    """Mock Agent config object used by Collector for test injection."""

    def __init__(self, global_min_interval):
        self._global_min = global_min_interval

    def __getitem__(self, key):
        # Allow Collector.set_loaders() to work without crashing
        if key == "additional_checksd":
            return "/dev/null"
        raise KeyError(key)

    def get(self, key, default=None):
        if key == "min_collection_interval":
            return self._global_min
        return default

    def get_check_configs(self):
        """Provide fake check configuration for testing."""
        return {
            "bundled": {
                "dummy_check": [
                    {
                        "init_config": {"min_collection_interval": 3},
                        "instances": [
                            {"min_collection_interval": 1},
                            {"min_collection_interval": 5},
                            {},
                            {"min_collection_interval": "fast"},
                        ],
                    }
                ]
            }
        }



# ----------------------------------------------------------------------
# Parameterized test for min_collection_interval behavior
# ----------------------------------------------------------------------

@pytest.mark.parametrize(
    "global_min, expected",
    [
        # global_min, expected [for instances 0..3]
        # 0: instance=1 (below global) -> clamped to global
        # 1: instance=5 (above global) -> stays 5
        # 2: instance={} -> uses init_config=3 -> clamped if below global
        # 3: instance="fast" -> invalid -> falls back to init=3 -> clamped if below global
        (4, [4, 5, 4, 4]),   # instance < global -> raised; invalid -> init(3) -> clamped(4)
        (2, [2, 5, 3, 3]),   # below global raised; invalid -> init(3) ok
        (15, [15, 15, 15, 15]),  # everything below global floor -> raised to 15
        (1, [1, 5, 3, 3]),   # only <1 bumped to 1; invalid -> init(3)
    ],
)
def test_min_collection_interval_clamping(global_min, expected):
    """Ensure min_collection_interval obeys instance, init, and global rules."""
    config = DummyConfig(global_min)
    collector = Collector(config)

    # Disable irrelevant Collector logic for this isolated test
    collector.set_loaders = lambda: None
    collector.CORE_CHECKS = []  # Avoid loading built-in core checks
    collector._check_classes = {"dummy_check": DummyCheck}
    collector._aggregator = None

    # Run instantiation, which applies global + local clamping logic
    collector.instantiate_checks()

    # Extract resulting effective min_collection_interval values
    instances = collector._check_instances["dummy_check"]
    actual = [c.min_collection_interval for c in instances]

    assert actual == expected, (
        f"Expected {expected} but got {actual} for global={global_min}"
    )
