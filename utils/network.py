# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import ipaddress
import os
import socket
import logging

from urllib.request import getproxies
from urllib.parse import urlparse, urlunparse
from socket import inet_pton

from config import config

IPPROTO_IPV6 = socket.IPPROTO_IPV6
IPV6_V6ONLY = socket.IPV6_V6ONLY
IPV6_DISABLED_ERR = "IPv6 is disabled"
LOCAL_PROXY_SKIP = ["127.0.0.1", "localhost", "169.254.169.254"]

log = logging.getLogger(__name__)


def _dd_proxy_env(name):
    """Read ``DD_PROXY_*``; treat empty string as unset. Uppercase fallback only."""
    v = os.environ.get(name)
    if v and str(v).strip():
        return v
    u = name.upper()
    v = os.environ.get(u)
    if v and str(v).strip():
        return v
    return None


def _resolve_proxy_scheme(dd_env_name, yaml_value, getproxies_dict, scheme_key):
    """
    Per-scheme proxy URL precedence::

        ``dd_env_name`` (e.g. ``DD_PROXY_HTTPS``)
        > ``yaml_value`` (``proxy.https`` in datadog.yaml)
        > ``getproxies_dict[scheme_key]`` (from ``HTTPS_PROXY`` / ``https_proxy`` / …).

    ``scheme_key`` is ``'http'`` or ``'https'`` as returned by ``urllib.request.getproxies()``.
    """
    return _dd_proxy_env(dd_env_name) or yaml_value or getproxies_dict.get(scheme_key)


def _split_dd_proxy_no_proxy(value):
    """
    Parse ``DD_PROXY_NO_PROXY``: comma/semicolon like ``NO_PROXY``, or
    whitespace-separated (Datadog docs) when no comma/semicolon present.
    """
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    if ',' in s or ';' in s:
        return _split_no_proxy_env_string(s)
    return [p for p in s.split() if p]


def _split_no_proxy_env_string(value):
    """
    Split a NO_PROXY / no_proxy environment-style value on commas and semicolons.
    (Only env and getproxies() ``no`` use this; datadog.yaml ``no_proxy`` uses a list.)
    """
    if value is None:
        return []
    s = str(value).strip()
    if not s:
        return []
    out = []
    for part in s.replace(';', ',').split(','):
        p = part.strip()
        if p:
            out.append(p)
    return out


def _no_proxy_yaml_tokens(val):
    """
    Tokens from ``proxy.no_proxy`` in datadog.yaml: a YAML list, or one literal
    string (commas are not split — use a list for multiple hosts).
    """
    if val is None:
        return []
    if isinstance(val, (list, tuple)):
        return [str(x).strip() for x in val if str(x).strip()]
    s = str(val).strip()
    return [s] if s else []


def should_bypass_proxy(url, no_proxy_uris):
    """
    Return True if ``url`` should bypass HTTP(S) proxies for the given
    ``no_proxy_uris`` (list of tokens, e.g. from NO_PROXY / proxy.no_proxy).

    Semantics follow ``datadog_checks.base.utils.http`` in integrations-core
    (DataDog/integrations-core#5081 and successors):

    - A list entry ``*`` matches all hosts (curl-style NOPROXY).
    - ``unix`` scheme URLs bypass (no HTTP proxy).
    - Tokens parsed as IPv4/IPv6 networks (``ipaddress``) match the URL host
      when it is a valid IP in that network (CIDR / netmask forms supported).
    - Otherwise tokens are host / domain rules: ``example.com`` matches that
      host and subdomains; a leading ``.`` or ``*.`` matches subdomains only
      (``.y.com`` matches ``x.y.com`` but not ``y.com``).
    """
    if not no_proxy_uris:
        return False

    parsed = urlparse(url)
    host = parsed.hostname

    if '*' in no_proxy_uris:
        return True

    if parsed.scheme == 'unix':
        return True

    if not host:
        return False

    host = host.lower()

    for raw_rule in no_proxy_uris:
        no_proxy_uri = (raw_rule or '').strip()
        if not no_proxy_uri:
            continue

        try:
            net = ipaddress.ip_network(no_proxy_uri, strict=False)
            addr = ipaddress.ip_address(host)
            if addr in net:
                return True
        except ValueError:
            rule = no_proxy_uri.lower()
            if rule.startswith(('.', '*.')):
                dot_no_proxy_uri = rule.lstrip('*')
            else:
                dot_no_proxy_uri = '.{}'.format(rule)
            if rule == host or host.endswith(dot_no_proxy_uri):
                return True

    return False


def ipv6_support():
    try:
        socket.inet_pton(socket.AF_INET6, "::1")
    except socket.error as e:
        if IPV6_DISABLED_ERR in str(e):
            return False
        raise e

    return True


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


def set_no_proxy_settings(proxy_settings, cfg_proxy):
    """
    Resolve ``no_proxy`` precedence (same stack as ``DD_PROXY_HTTP`` / main Agent):

    1. ``DD_PROXY_NO_PROXY`` — if set (non-empty), use only that (parsed).
    2. Else ``proxy.no_proxy`` from datadog.yaml (YAML list or one literal string).
    3. Else ``NO_PROXY`` / ``no_proxy`` environment variables.

    Then append ``LOCAL_PROXY_SKIP`` unless the chosen list contains ``*``.
    """
    dd_np = _dd_proxy_env('DD_PROXY_NO_PROXY')
    if dd_np and str(dd_np).strip():
        no_proxy = list(_split_dd_proxy_no_proxy(dd_np))
    elif cfg_proxy.get('no_proxy') is not None:
        no_proxy = list(_no_proxy_yaml_tokens(cfg_proxy.get('no_proxy')))
    else:
        no_proxy = list(_split_no_proxy_env_string(
            os.environ.get('no_proxy') or os.environ.get('NO_PROXY') or ''
        ))

    bypass_all = '*' in no_proxy
    if not bypass_all:
        for host in LOCAL_PROXY_SKIP:
            if host not in no_proxy:
                no_proxy.append(host)

    merged = ','.join(no_proxy)
    proxy_settings['no_proxy'] = merged
    os.environ['no_proxy'] = merged
    # Avoid duplicating urllib's `no` key; requests ignores both for scheme proxies
    # until http.RequestsWrapper clears http/https. Single key keeps logs/config clear.
    proxy_settings.pop('no', None)


def get_proxy():
    """
    HTTP/HTTPS proxy URL precedence (each scheme independently), aligned with the
    main Datadog Agent / docs::

        ``DD_PROXY_HTTP``  > ``proxy.http``  (datadog.yaml) > ``http_proxy`` / ``HTTP_PROXY`` / …
        ``DD_PROXY_HTTPS`` > ``proxy.https`` (datadog.yaml) > ``https_proxy`` / ``HTTPS_PROXY`` / …

    The third tier is whatever ``urllib.request.getproxies()`` exposes for that
    scheme (standard ``*_proxy`` environment variables).

    ``no_proxy`` is resolved in ``set_no_proxy_settings`` using::

        ``DD_PROXY_NO_PROXY`` > ``proxy.no_proxy`` (yaml) > ``NO_PROXY`` / ``no_proxy`` env.
    """
    cfg = config.get('proxy', {}) or {}
    gp = getproxies()

    http = _resolve_proxy_scheme('DD_PROXY_HTTP', cfg.get('http'), gp, 'http')
    https = _resolve_proxy_scheme('DD_PROXY_HTTPS', cfg.get('https'), gp, 'https')

    proxy_settings = {}
    if http:
        proxy_settings['http'] = http
    if https:
        proxy_settings['https'] = https

    # Preserve odd ``*_proxy`` keys from the OS only when yaml/DD did not set http/https.
    if not proxy_settings.get('http') and not proxy_settings.get('https') and gp:
        proxy_settings = dict(gp)

    set_no_proxy_settings(proxy_settings, cfg)
    return proxy_settings


def config_proxy_skip(proxies, uri, skip_proxy=False):
    """
    Returns an amended copy of the proxies dictionary - used by `requests`,
    it will disable the proxy if the uri provided is to be reached directly.

    Keyword Arguments:
        proxies -- dict with existing proxies: 'https', 'http', 'no_proxy' (or legacy 'no')
        uri -- uri to determine if proxy is necessary or not.
        skip_proxy -- if True, the proxy dictionary returned will disable all proxies
    """
    parsed_uri = urlparse(uri)

    # disable proxy if necessary
    # keep keys so `requests` doesn't use env var proxies either
    if skip_proxy:
        proxies['http'] = None
        proxies['https'] = None
    elif proxies.get('no_proxy') or proxies.get('no'):
        skip_src = proxies.get('no_proxy') or proxies.get('no') or ''
        if isinstance(skip_src, (list, tuple)):
            skip_parts = [str(x).strip() for x in skip_src if str(x).strip()]
        else:
            skip_parts = [p.strip() for p in str(skip_src).replace(';', ',').split(',') if p.strip()]
        for url in skip_parts:
            if url in parsed_uri.netloc:
                proxies['http'] = None
                proxies['https'] = None

    return proxies


def get_site_url(uri, site=''):
    if not site:
        return uri

    parsed_uri = urlparse(uri)
    domain = parsed_uri.netloc or parsed_uri.path
    if not domain:
        raise TypeError("unexpected or invalid uri format")

    # TODO: add support for three part domain names (currently only 2-part roots are supported)
    domain_parts = domain.split('.')
    if len(domain_parts) > 2:
        site_domain = "{service}.{site}".format(
            service='.'.join(domain_parts[0:-2]),
            site=site
        )
    else:
        site_domain = site

    if parsed_uri.netloc:
        parsed_uri = parsed_uri._replace(netloc=site_domain)
    else:
        parsed_uri = parsed_uri._replace(path=site_domain)

    return urlunparse(parsed_uri)
