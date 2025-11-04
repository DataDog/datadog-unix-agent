import requests
import logging
import traceback
import urllib3
from config import config
from config.config import AGENT_VERSION
from utils.network import get_proxy

log = logging.getLogger(__name__)


class RequestsWrapper:
    __slots__ = (
        '_session',
        'options',
    )

    def __init__(self):
        self._session = requests.Session()

        proxies = get_proxy()
        verify = not config.get('skip_ssl_validation')
        timeout = 10  # default timeout in seconds

        # Standard headers
        headers = {
            "User-Agent": f"datadog-unix-agent/{AGENT_VERSION}",
        }

        self.options = {
            "headers": headers,
            "proxies": proxies,
            "timeout": timeout,
            "verify": verify,
        }

        # Disable SSL warnings only when validation is skipped
        if not verify:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            log.warning(
                "[HTTP] SSL verification disabled; suppressing InsecureRequestWarning")

    # --------------------------------------------------------------------------
    # Centralized request handler with safe error logging
    # --------------------------------------------------------------------------
    def request(self, method, url, **kwargs):
        """Send an HTTP request with safe error logging (does not swallow exceptions)."""

        merged = self.options.copy()
        merged.update(kwargs)
        headers = merged["headers"].copy()

        # Mask API key for logging
        safe_headers = dict(headers)
        if "DD-API-KEY" in safe_headers:
            api_key = safe_headers["DD-API-KEY"]
            if isinstance(api_key, str) and len(api_key) >= 5:
                if len(api_key) == 32 and api_key.isalnum():
                    safe_headers["DD-API-KEY"] = '*' * 27 + api_key[-5:]
                else:
                    safe_headers["DD-API-KEY"] = '*' * \
                        max(0, len(api_key) - 5) + api_key[-5:]

        # Debug request configuration
        log.debug(
            "[HTTP] %s %s; verify=%s; proxies=%s; timeout=%s; headers=%s",
            method, url, merged["verify"], merged["proxies"], merged["timeout"], safe_headers,
        )

        # Return response
        try:
            return self._session.request(method, url, **merged)
        except requests.exceptions.RequestException as e:
            # Centralized transport-level traceback logging
            log.debug(
                "[HTTP] Transport error during %s %s: %s\nTraceback:\n%s",
                method, url, e, traceback.format_exc()
            )
            raise  # re-raise so Transaction can handle retries/drop logic

    def get(self, url, **kwargs):
        """Convenience method for GET requests."""
        return self.request("GET", url, **kwargs)

    def post(self, url, **kwargs):
        """Convenience method for POST requests."""
        return self.request("POST", url, **kwargs)


# -------------------------------------------------------------------
# Lazy initialization for shared singleton instance
# -------------------------------------------------------------------
_shared_requests = None


def get_shared_requests():
    """
    Return a shared RequestsWrapper instance.
    Lazily creates it on first use to ensure config is fully loaded.
    """
    global _shared_requests
    if _shared_requests is None:
        _shared_requests = RequestsWrapper()
    return _shared_requests
