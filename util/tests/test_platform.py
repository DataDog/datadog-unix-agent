import mock

from util.platform import Platform, get_os


@mock.patch("sys.platform", return_value="freebsd")
def get_os_freebsd(platform):
    assert get_os() == "freebsd"

@mock.patch("sys.platform", return_value="linux")
def get_os_linux(platform):
    assert get_os() == "linux"

@mock.patch("sys.platform", return_value="sunos")
def get_os_sunos(platform):
    assert get_os() == "sunos"

@mock.patch("sys.platform", return_value="test-value")
def get_os_custom(platform):
    assert get_os() == "test-value"

# TODO: test Platform
