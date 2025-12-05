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

    # Mock CPU (AIX-like)
    mock_cpu.return_value = {
        "cpu_cores": "8",
        "cpu_logical_processors": "8",
        "model_name": "POWER9",
        "mhz": "3800",
        "vendor_id": "PowerPC"
    }

    # Mock filesystem
    mock_fs.return_value = [
        {"name": "/dev/hd4", "mounted_on": "/", "kb_size": "10485760"},
    ]

    # Mock memory
    mock_memory.return_value = {
        "total": "17179869184",
        "swap_total": "4194304kB",
    }

    # Mock network
    mock_network.return_value = {
        "interfaces": [
            {
                "name": "en0",
                "macaddress": "00:11:22:33:44:55",
                "ipv4": ["10.0.0.5"],
                "ipv4-network": "255.255.255.0"
            }
        ],
        "ipaddress": "10.0.0.5",
        "macaddress": "00:11:22:33:44:55"
    }

    # Mock platform
    mock_platform.return_value = {
        "hostname": "test-aix",
        "os": "AIX",
        "machine": "ppc64le",
        "processor": "POWER9",
        "pythonV": "3.9.0",
        "hardware_platform": "IBM Power System (emulated)",
        "kernel_version": "7.2",
        "kernel_release": "7200-04-02-2027"
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

    # --- Validate mocked values ---

    # CPU
    assert inner["cpu"]["model_name"] == "POWER9"
    assert inner["cpu"]["cpu_cores"] == "8"

    # Filesystem
    assert inner["filesystem"][0]["mounted_on"] == "/"

    # Memory
    assert inner["memory"]["total"] == "17179869184"

    # Network
    assert inner["network"]["macaddress"] == "00:11:22:33:44:55"
    assert inner["network"]["interfaces"][0]["ipv4"][0] == "10.0.0.5"

    # Platform
    assert inner["platform"]["os"] == "AIX"
    assert inner["platform"]["kernel_version"] == "7.2"
    assert inner["platform"]["kernel_release"] == "7200-04-02-2027"
    assert inner["platform"]["processor"] == "POWER9"


@patch("metadata.gohai.collect_gohai")
def test_gohai_collectors_not_called_when_disabled(mock_collect_gohai):
    config.data = {"enable_gohai": False}
    config.defaults = {}

    result = get_metadata("test-host", AGENT_VERSION)

    assert "gohai" not in result
    mock_collect_gohai.assert_not_called()
