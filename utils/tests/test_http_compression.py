import pytest
import json
import logging
from utils import http

class DummySession:
    def __init__(self):
        self.last_post = None
    def request(self, method, url, **kwargs):
        self.last_post = (method, url, kwargs)
        class DummyResponse:
            status_code = 202
            text = "ok"
        return DummyResponse()


@pytest.fixture(autouse=True)
def setup_logger(caplog):
    caplog.set_level(logging.INFO)
    yield
    caplog.clear()


def test_compress_with_zlib_basic():
    data = b"x" * 10000
    compressed, encoding = http._compress_with_zlib(data)
    assert encoding == "deflate"
    assert len(compressed) < len(data)


@pytest.mark.skipif(not http.HAS_ZSTD, reason="zstandard not available")
def test_compress_with_zstd_basic():
    data = b"x" * 10000
    compressed, encoding = http._compress_with_zstd(data)
    assert encoding == "zstd"
    assert len(compressed) < len(data)


def test_compress_payload_reduces_size(caplog):
    # Ensure module logger is captured
    logger = logging.getLogger("utils.http")
    logger.setLevel(logging.DEBUG)

    data = b"x" * 10000
    compressed, encoding = http._compress_payload(
        data, http._compress_with_zlib, endpoint="/fake/series"
    )

    assert encoding == "deflate"
    assert len(compressed) < len(data)

    # caplog automatically captures log records now
    assert "Compression check [/fake/series]" in caplog.text


def test_compress_payload_skips_if_larger(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG, logger="utils.http")

    def fake_compress(data, level=None):
        return data + b"EXTRA", "deflate"

    monkeypatch.setattr(http, "_compress_with_zlib", fake_compress)

    data = b"abc" * 10
    compressed, encoding = http._compress_payload(
        data, http._compress_with_zlib, endpoint="/fake/intake"
    )

    assert encoding is None
    assert compressed == data
    assert "Compression skipped [/fake/intake]" in caplog.text


def test_request_applies_compression(monkeypatch):
    session = DummySession()
    monkeypatch.setattr(http.requests, "Session", lambda: session)
    wrapper = http.RequestsWrapper()

    data = json.dumps({"series": ["x" * 10000]})  # large enough to compress
    resp = wrapper.request("POST", "https://unix.agent.datadoghq.com/api/v1/series", data=data)
    assert resp.status_code == 202

    method, url, kwargs = session.last_post
    headers = kwargs["headers"]

    if "Content-Encoding" in headers:
        assert headers["Content-Encoding"] in ("zstd", "deflate")
        assert isinstance(kwargs["data"], (bytes, bytearray))
    else:
        # Compression skipped (payload too small)
        assert kwargs["data"] == data
