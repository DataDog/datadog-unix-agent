import json
import requests
import logging
import traceback
import urllib3
import zlib
from config import config
from config.config import AGENT_VERSION
from typing import Optional
from urllib.parse import urlparse
from utils.network import get_proxy
from utils.util import _is_affirmative
from utils.strip import mask_api_key_value

try:
    import zstandard as zstd
    HAS_ZSTD = True
except ImportError:
    HAS_ZSTD = False

log = logging.getLogger(__name__)


# -------------------------------------------------------------------
# Compression constants (aligned with backend limits)
# -------------------------------------------------------------------
MAX_COMPRESSED_SIZE = 2 << 20  # 2 MB – conservative limit
MAX_SPLIT_DEPTH = 2            # for future payload-splitting logic


def _compress_with_zstd(data: bytes, level: Optional[int] = None):
    """Compress payload using Zstandard."""
    level = level or 1
    cctx = zstd.ZstdCompressor(level=level)
    return cctx.compress(data), "zstd"


def _compress_with_zlib(data: bytes, level: Optional[int] = None):
    """Compress payload using zlib (deflate)."""
    return zlib.compress(data, zlib.Z_DEFAULT_COMPRESSION), "deflate"


def _compress_payload(
    data: bytes,
    compress_func,
    level: Optional[int] = None,
    endpoint: Optional[str] = None
):
    """
    Compress payload using the provided compression function.
    Returns (compressed_bytes, content_encoding).
    Logs compression ratio and endpoint context.
    """
    if not data:
        return data, None

    compressed, encoding = compress_func(data, level)
    orig_size = len(data)
    comp_size = len(compressed)
    ratio = (comp_size / orig_size) * 100 if orig_size else 0.0

    # If compression yields a larger payload, skip
    if comp_size >= orig_size:
        log.debug(
            "[HTTP] Compression skipped%s: kind=%s increased size (%d -> %d, %.1f%% of original)",
            f" [{endpoint}]" if endpoint else "",
            encoding,
            orig_size,
            comp_size,
            ratio,
        )
        return data, None

    # Log compression ratio
    log.debug(
        "[HTTP] Compression check%s: kind=%s, before=%d bytes, after=%d bytes (%.1f%% of original)",
        f" [{endpoint}]" if endpoint else "",
        encoding,
        orig_size,
        comp_size,
        ratio,
    )

    return compressed, encoding


class RequestsWrapper:
    """
    Lightweight HTTP wrapper for integrations and the forwarder.

    Integrations MUST create their own instance of RequestsWrapper.
    The forwarder uses get_shared_requests() with compression enabled.

    Parameters:
        use_compression (bool): Enable payload compression (default: False).
        compression_kind (str): "zstd" (preferred) or "zlib".
        compression_level (int): zstd compression level (ignored for zlib).
        default_content_type (str|None): If set, overrides the request Content-Type
                                         when compression is applied. Integrations
                                         should usually leave this as None and
                                         provide their own Content-Type via config.

    Integration example:

        comp_cfg = self.instance.get("compression", {}) or {}
        hdrs = self.instance.get("headers", {}) or {}

        wrapper = RequestsWrapper(
            use_compression=comp_cfg.get("use_compression", False),
            compression_kind=comp_cfg.get("compression_kind", "zstd"),
            compression_level=comp_cfg.get("compression_level", 1),
            default_content_type=None,   # integration manages Content-Type
        )

        resp = wrapper.post(
            self.instance.get("url"),
            data=payload,
            headers=hdrs,
        )
    """
    __slots__ = (
        '_session',
        'options',
        '_use_compression',
        '_compress_func',
        '_compression_level',
        '_default_content_type',
    )

    def __init__(
        self,
        use_compression: bool = False,
        compression_kind: str = "zstd",
        compression_level: int = 1,
        default_content_type=None,
    ):
        self._session = requests.Session()
        self._default_content_type = default_content_type

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

        # ----- Compression config -----
        self._use_compression = bool(use_compression)
        self._compress_func = None
        self._compression_level = None

        if self._use_compression:
            kind = (compression_kind or "zstd").lower()

            if HAS_ZSTD and kind != "zlib":
                self._compress_func = _compress_with_zstd
                self._compression_level = compression_level
                log.debug(
                    "[HTTP] Compression initialized with zstd (level=%s)",
                    self._compression_level,
                )
            else:
                self._compress_func = _compress_with_zlib
                msg = (
                    "[HTTP] zstandard not available; using zlib fallback"
                    if compression_kind == "zstd" and not HAS_ZSTD
                    else "[HTTP] Compression initialized with zlib"
                )
                log.warning(msg) if "fallback" in msg else log.debug(msg)

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
        data = merged.get("data", None)

        # Mask API key for logging
        safe_headers = dict(headers)
        if "DD-API-KEY" in safe_headers:
            safe_headers["DD-API-KEY"] = mask_api_key_value(safe_headers["DD-API-KEY"])

        # Debug request configuration
        log.debug(
            "[HTTP] %s %s; verify=%s; proxies=%s; timeout=%s; headers=%s",
            method, url, merged["verify"], merged["proxies"], merged["timeout"], safe_headers,
        )

        # ----------------------------------------------------------------------
        # Optional payload compression (POST/PUT with data)
        # ----------------------------------------------------------------------
        encoding = None
        endpoint = urlparse(url).path

        if self._compress_func and method in ("POST", "PUT"):
            try:
                # Convert to bytes
                if isinstance(data, (dict, list, tuple)):
                    data_bytes = json.dumps(data).encode("utf-8")
                elif isinstance(data, str):
                    data_bytes = data.encode("utf-8")
                elif isinstance(data, (bytes, bytearray)):
                    data_bytes = data
                else:
                    raise TypeError(f"Unsupported payload type: {type(data)}")

                compressed, encoding = _compress_payload(
                    data_bytes, self._compress_func, self._compression_level, endpoint
                )

                if encoding:
                    headers["Content-Encoding"] = encoding

                # Use forwarder-configured type OR preserve caller type
                if self._default_content_type:
                    headers["Content-Type"] = self._default_content_type

                merged["data"] = compressed

            except Exception as e:
                log.warning(
                    "[HTTP] [%s] Compression failed (%s); sending uncompressed",
                    endpoint,
                    e,
                )
                headers.pop("Content-Encoding", None)
                merged["data"] = data
        else:
            merged["data"] = data

        merged["headers"] = headers

        # ----------------------------------------------------------------------
        # Actual HTTP request with safe error handling
        # ----------------------------------------------------------------------
        try:
            # NOTE: In the future, larger payloads (HTTP 413) could be handled via
            # payload splitting logic. For now, compression already minimizes size,
            # and retrying uncompressed would only make the payload larger.
            return self._session.request(method, url, **merged)

        except requests.exceptions.RequestException as e:
            # Centralized transport-level traceback logging
            log.debug(
                "[HTTP] Transport error during %s %s: %s\nTraceback:\n%s",
                method,
                url,
                e,
                traceback.format_exc(),
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
    Return the shared RequestsWrapper used exclusively by the forwarder.

    This wrapper is initialized once and configured using the `forwarder`
    section of the main agent config. The forwarder always sends JSON
    payloads, so compression is enabled by default and the Content-Type
    is fixed to "application/json".

    Note:
        Integrations MUST NOT use this shared instance. They should
        create their own RequestsWrapper with integration-specific
        compression and header settings.

    Lazily creates the instance on first use to ensure config is loaded.
    """
    global _shared_requests
    if _shared_requests is None:
        fwd = config.get("forwarder", {}) or {}
        _shared_requests = RequestsWrapper(
            use_compression=_is_affirmative(fwd.get("use_compression", True)),
            compression_kind=fwd.get("compression_kind", "zstd"),
            compression_level=fwd.get("compression_level", 1),
            default_content_type="application/json",
        )
    return _shared_requests


def get_flare_requests():
    """
    Return a fresh RequestsWrapper instance suitable for flare uploads.

    Flare submits multipart/form-data with a binary archive, so:
      * compression must always be disabled
      * Content-Type must NOT be overridden (requests will set multipart
        boundaries automatically)
    """
    return RequestsWrapper(use_compression=False)
