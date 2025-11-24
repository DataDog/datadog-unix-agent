import json
import pytest
from unittest.mock import patch

from metadata.metadata import get_metadata
from config import config
from config.config import AGENT_VERSION


@pytest.fixture(autouse=True)
def reset_config():
    """
    Automatically reset config before each test to avoid leakage between tests.
    """
    config.data = {}
    config.defaults = {}
    yield


@patch("metadata.gohai.collect_cpu")
@patch("metadata.gohai.collect_filesystem")
@patch("metadata.gohai.collect_memory")
@patch("metadata.gohai.collect_network")
@patch("metadata.gohai.collect_platform")
def test_gohai_with_mocked_collectors(
    mock_platform,
    mock_network,
    mock_memory,
    mock_fs,
    mock_cpu
):
    """
    Validate that:
      - gohai is included when enable_gohai=True
      - it is a valid JSON string
      - decoded JSON contains required keys
      - mocked collector values appear in the final payload
    """

    # Mock values (AIX-like example)
    mock_cpu.return_value = {
        "cpu_cores": "8",
        "model_name": "POWER9",
    }

    mock_fs.return_value = [
        {"name": "/dev/hd4", "mounted_on": "/", "kb_size": "10485760"},
    ]

    mock_memory.return_value = {
        "total": "17179869184",
        "swap_total": "4194304kB",
    }

    mock_network.return_value = {
        "ipaddress": "10.0.0.5",
        "ipaddressv6": "fe80::1234",
        "macaddress": "00:11:22:33:44:55",
    }

    mock_platform.return_value = {
        "GOOARCH": "ppc64le",
        "GOOS": "aix",
        "hostname": "test-aix",
        "kernel_name": "AIX",
        "kernel_release": "7.2",
        "kernel_version": "7300-01-01-2345",
        "machine": "ppc64le",
        "os": "AIX",
        "processor": "powerpc",
        "pythonV": "3.9.0",
        "goV": "",
    }

    # Enable gohai
    config.set("enable_gohai", True)

    metadata = get_metadata("test-aix-host", AGENT_VERSION)

    # gohai must be present
    assert "gohai" in metadata, "gohai must be included when enable_gohai=True"

    gohai_str = metadata["gohai"]

    # gohai must be a JSON string (not a dict)
    assert isinstance(gohai_str, str), "gohai should be a JSON string"

    # Parse the inner JSON
    inner = json.loads(gohai_str)

    # Final inner structure must be a dictionary
    assert isinstance(inner, dict), "Decoded gohai must be a dict"

    # Required top-level keys
    expected_keys = {"cpu", "filesystem", "memory", "network", "platform"}
    assert expected_keys.issubset(inner.keys()), \
        f"Expected keys missing: {expected_keys - set(inner.keys())}"

    # Verify mocked values appear in the final gohai payload
    assert inner["cpu"]["model_name"] == "POWER9"
    assert inner["platform"]["GOOS"] == "aix"
    assert inner["network"]["macaddress"] == "00:11:22:33:44:55"
    assert inner["filesystem"][0]["mounted_on"] == "/"
    assert inner["memory"]["total"] == "17179869184"
