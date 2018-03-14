# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import mock

from utils.platform import get_os


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
