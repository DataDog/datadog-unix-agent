# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from utils.platform import (
    get_os,
    running_root
)


@mock.patch("utils.platform.OS_PLATFORM", "freebsd")
def test_get_os_freebsd():
    assert get_os() == "freebsd"


@mock.patch("utils.platform.OS_PLATFORM", "linux")
def test_get_os_linux():
    assert get_os() == "linux"


@mock.patch("utils.platform.OS_PLATFORM", "sunos")
def test_get_os_sunos():
    assert get_os() == "solaris"


@mock.patch("utils.platform.OS_PLATFORM", "aix6")
def test_get_os_aix6():
    assert get_os() == "aix"


@mock.patch("utils.platform.OS_PLATFORM", "aix7")
def test_get_os_aix7():
    assert get_os() == "aix"


@mock.patch("utils.platform.OS_PLATFORM", "test-value")
def test_get_os_custom():
    assert get_os() == "test-value"


@mock.patch("os.getuid", return_value=0)
def test_running_root(fixture):
    assert running_root()

# TODO: test Platform
