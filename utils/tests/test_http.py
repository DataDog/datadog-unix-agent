import pytest
from unittest.mock import patch, MagicMock
import urllib3

# Module under test + helper module refs
import utils.http as http_module
from utils.http import RequestsWrapper
from forwarder.forwarder import Forwarder


# ---------------------------- Fixtures ---------------------------------

@pytest.fixture(autouse=True)
def reset_shared_requests(monkeypatch):
    """
    Ensure each test gets a fresh RequestsWrapper (singleton) instance.
    This avoids cross-test leakage of options like proxies.
    """
    monkeypatch.setattr(http_module, "_shared_requests", None, raising=False)


# ---------------------------- Tests: RequestsWrapper --------------------

def test_request_calls_session(monkeypatch):
    # Avoid config side-effects
    monkeypatch.setattr("config.config.get", lambda key, default=None: False)
    monkeypatch.setattr("utils.http.get_proxy", lambda: {})

    wrapper = RequestsWrapper()

    mock_response = MagicMock()
    mock_response.status_code = 200

    with patch.object(wrapper._session, "request", return_value=mock_response) as mock_request:
        resp = wrapper.request("GET", "https://example.com")

        mock_request.assert_called_once_with(
            "GET",
            "https://example.com",
            headers=wrapper.options["headers"],
            proxies=wrapper.options["proxies"],
            timeout=wrapper.options["timeout"],
            verify=wrapper.options["verify"],
        )
        assert resp is mock_response


@pytest.mark.parametrize(
    "skip_flag, expected_verify, warn_called",
    [
        (True,  False, True),   # skip => verify=False, warnings suppressed
        (False, True,  False),  # normal => verify=True, no suppression
    ],
)
def test_verify_depends_on_skip_ssl_validation(monkeypatch, skip_flag, expected_verify, warn_called):
    # Prevent proxy lookups
    monkeypatch.setattr("utils.http.get_proxy", lambda: {})

    # Control the skip flag via config.get
    monkeypatch.setattr(
        "config.config.get",
        lambda key, default=None: skip_flag if key == "skip_ssl_validation" else default,
    )

    # Track warning suppression calls
    called = {"disabled": False}

    def fake_disable_warnings(arg):
        called["disabled"] = True

    monkeypatch.setattr(urllib3, "disable_warnings", fake_disable_warnings)

    wrapper = RequestsWrapper()
    assert wrapper.options["verify"] is expected_verify
    assert called["disabled"] is warn_called


@pytest.mark.parametrize(
    "proxies",
    [
        {"http": "http://fake-proxy:8080",
         "https": "https://fake-proxy:8080",
         "no_proxy": "localhost,127.0.0.1"},
        {},  # empty proxies
    ],
)
def test_requests_wrapper_proxies(monkeypatch, proxies):
    # Avoid unrelated config paths
    monkeypatch.setattr("config.config.get", lambda key, default=None: False)
    # Patch the reference used *inside* utils.http
    monkeypatch.setattr("utils.http.get_proxy", lambda: proxies)

    wrapper = RequestsWrapper()
    assert wrapper.options["proxies"] == proxies


# ---------------------------- Tests: Forwarder → Transaction --------------------

@pytest.mark.parametrize(
    "forwarder_timeout, opts_timeout",
    [
        (None, 20),
        (15, 15)
    ],
)
def test_forwarder_uses_custom_forwarder_timeout(monkeypatch, forwarder_timeout, opts_timeout):
    """Forwarder._submit_payload should inject config.get('forwarder_timeout') into options."""

    with patch("forwarder.forwarder.Transaction") as mock_tx:
        if forwarder_timeout:
            fwd = Forwarder("api_key", "https://unix.agent.datadoghq.com", forwarder_timeout)
        else:
            fwd = Forwarder("api_key", "https://unix.agent.datadoghq.com")
        fwd._submit_payload("/api/v1/series", "payload_data", {"Custom": "X"})

        mock_tx.assert_called_once()
        _, kwargs = mock_tx.call_args
        opts = kwargs["options"]

        assert opts["timeout"] == opts_timeout
        assert opts["headers"]["DD-API-KEY"] == "api_key"
        assert opts["headers"]["Custom"] == "X"


def test_forwarder_passes_proxies_to_transaction(monkeypatch):
    """Proxies from RequestsWrapper propagate into Transaction options."""
    fake_proxies = {
        "http": "http://proxy.example.com:8080",
        "https": "https://proxy.example.com:8080",
        "no_proxy": "localhost,127.0.0.1",
    }

    # Patch where it's USED by utils.http
    monkeypatch.setattr("utils.http.get_proxy", lambda: fake_proxies)

    with patch("forwarder.forwarder.Transaction") as mock_tx:
        fwd = Forwarder("api_key", "https://unix.agent.datadoghq.com")
        fwd._submit_payload("/api/v1/series", "payload_data", {"Custom": "X"})

        mock_tx.assert_called_once()
        _, kwargs = mock_tx.call_args
        opts = kwargs["options"]

        assert opts["proxies"] == fake_proxies
        assert opts["headers"]["DD-API-KEY"] == "api_key"
        assert opts["headers"]["Custom"] == "X"
