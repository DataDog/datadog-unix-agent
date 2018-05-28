# Unless explicitly stated otherwise all files in this repository are licensed

# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import socket
import logging

from urllib import getproxies
from urlparse import urlparse
from socket import inet_pton

from config import config

IPPROTO_IPV6 = socket.IPPROTO_IPV6
IPV6_V6ONLY = socket.IPV6_V6ONLY
IPV6_DISABLED_ERR = "IPv6 is disabled"


def ipv6_support():
    try:
        socket.inet_pton(socket.AF_INET6, "::1")
    except socket.error as e:
        if IPV6_DISABLED_ERR in str(e):
            return False
        raise e

    return True

log = logging.getLogger(__name__)


def mapto_v6(addr):
    """
    Map an IPv4 address to an IPv6 one.
    If the address is already an IPv6 one, just return it.
    Return None if the IP address is not valid.
    """
    try:
        inet_pton(socket.AF_INET, addr)
        return '::ffff:{}'.format(addr)
    except socket.error:
        try:
            inet_pton(socket.AF_INET6, addr)
            return addr
        except socket.error:
            logging.debug('%s is not a valid IP address.', addr)

    return None


def get_socket_address(host, port, ipv4_only=False):
    """
    Gather informations to open the server socket.
    Try to resolve the name giving precedence to IPv4 for retro compatibility
    but still mapping the host to an IPv6 address, fallback to IPv6.
    """
    try:
        info = socket.getaddrinfo(host, port, socket.AF_INET, socket.SOCK_DGRAM)
    except socket.gaierror as e:
        try:
            if not ipv4_only:
                info = socket.getaddrinfo(host, port, socket.AF_INET6, socket.SOCK_DGRAM)
            elif host == 'localhost':
                logging.warning("Warning localhost seems undefined in your host file, using 127.0.0.1 instead")
                info = socket.getaddrinfo('127.0.0.1', port, socket.AF_INET, socket.SOCK_DGRAM)
            else:
                logging.error('Error processing host %s and port %s: %s', host, port, e)
                return None
        except socket.gaierror as e:
            logging.error('Error processing host %s and port %s: %s', host, port, e)
            return None

    # we get the first item of the list and map the address for IPv4 hosts
    sockaddr = info[0][-1]
    if info[0][0] == socket.AF_INET and not ipv4_only:
        mapped_host = mapto_v6(sockaddr[0])
        sockaddr = (mapped_host, sockaddr[1], 0, 0)
    return sockaddr


def set_no_proxy_settings(proxy_settings):

    to_add = ["127.0.0.1", "localhost", "169.254.169.254"]
    no_proxy = os.environ.get('no_proxy', os.environ.get('NO_PROXY', None))

    if no_proxy is None or not no_proxy.strip():
        no_proxy = []
    else:
        no_proxy = no_proxy.split(',')

    for host in to_add:
        if host not in no_proxy:
            no_proxy.append(host)

    for host in proxy_settings.get('no_proxy', '').split(','):
        if host not in no_proxy:
            no_proxy.append(host)

    proxy_settings['no_proxy'] = ','.join(no_proxy)
    os.environ['no_proxy'] = proxy_settings['no_proxy']


def get_proxy():
    proxy_settings = config.get('proxy', {})

    # if nothing was set, use OS-level proxies
    if not proxy_settings:
        proxy_settings = getproxies()

    # remove anything local...
    if proxy_settings:
        set_no_proxy_settings(proxy_settings)

    return proxy_settings


def config_proxy_skip(proxies, uri, skip_proxy=False):
    """
    Returns an amended copy of the proxies dictionary - used by `requests`,
    it will disable the proxy if the uri provided is to be reached directly.

    Keyword Arguments:
        proxies -- dict with existing proxies: 'https', 'http', 'no' as pontential keys
        uri -- uri to determine if proxy is necessary or not.
        skip_proxy -- if True, the proxy dictionary returned will disable all proxies
    """
    parsed_uri = urlparse(uri)

    # disable proxy if necessary
    # keep keys so `requests` doesn't use env var proxies either
    if skip_proxy:
        proxies['http'] = None
        proxies['https'] = None
    elif proxies.get('no'):
        for url in proxies['no'].replace(';', ',').split(","):
            if url in parsed_uri.netloc:
                proxies['http'] = None
                proxies['https'] = None

    return proxies
