# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

from utils.network import (
    mapto_v6,
    get_socket_address,
)


def test_mapto_v6():
    addr4 = "8.8.8.8"
    addr4_6 = mapto_v6(addr4)

    assert addr4_6
    assert addr4 != addr4_6
    assert addr4_6.startswith('::ffff:')

    addr6 = "2001:4860:4860::8888"
    addr6_6 = mapto_v6(addr6)
    assert addr6_6
    assert addr6 == addr6_6

    addr_bad = "2001:4860:4860::8888:badadd"
    addrbad_6 = mapto_v6(addr_bad)
    assert addrbad_6 is None


def test_get_socket_address():
    addr4 = "8.8.8.8"
    addr6 = "2001:4860:4860::8888"
    port = 53

    sockaddr = get_socket_address(addr4, port)
    assert sockaddr
    assert len(sockaddr) == 4
    assert sockaddr[0] == mapto_v6(addr4)
    assert sockaddr[1] == port

    sockaddr = get_socket_address(addr6, port)
    assert sockaddr
    assert len(sockaddr) == 4
    assert sockaddr[0] == addr6
    assert sockaddr[1] == port

    sockaddr = get_socket_address(addr4, port, ipv4_only=True)
    assert sockaddr
    assert len(sockaddr) == 2
    assert sockaddr[0] == addr4
    assert sockaddr[1] == port

    sockaddr = get_socket_address(addr6, port, ipv4_only=True)
    assert sockaddr is None
