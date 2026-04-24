# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

try:
    import mock
except ImportError:
    from unittest import mock

import os
from urllib.parse import urlparse

from utils.network import (
    mapto_v6,
    get_socket_address,
    get_proxy,
    get_site_url,
    LOCAL_PROXY_SKIP,
    should_bypass_proxy,
    _no_proxy_yaml_tokens,
    _split_no_proxy_env_string,
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


def test_get_proxy():
    from config import config
    config['proxy'] = None

    with mock.patch('utils.network.getproxies', return_value={}):
        proxy_settings = get_proxy()
        assert 'http' not in proxy_settings
        assert 'https' not in proxy_settings
        assert 'no_proxy' in proxy_settings
        for host in LOCAL_PROXY_SKIP:
            assert host in proxy_settings['no_proxy'].split(',')

    # remove all config options
    del config['proxy']
    del config.defaults['proxy']

    with mock.patch('utils.network.getproxies', return_value={}):
        proxy_settings = get_proxy()
        assert 'http' not in proxy_settings
        assert 'https' not in proxy_settings
        assert 'no_proxy' in proxy_settings
        for host in LOCAL_PROXY_SKIP:
            assert host in proxy_settings['no_proxy'].split(',')

    # restore defaults
    config.defaults['proxy'] = {
        'http': None,
        'https': None,
    }
    config['proxy'] = {
        'http': 'http://foo',
        'https': 'http://bar',
    }

    proxy_settings = get_proxy()
    assert proxy_settings is not {}
    assert 'http' in proxy_settings
    assert proxy_settings['http'] == 'http://foo'
    assert 'https' in proxy_settings
    assert proxy_settings['https'] == 'http://bar'
    assert 'no_proxy' in proxy_settings
    assert 'no' not in proxy_settings

    no_proxy = proxy_settings['no_proxy'].split(',')
    for host in LOCAL_PROXY_SKIP:
        assert host in no_proxy


def test_get_proxy_from_env():
    from config import config
    config.reset('proxy')

    proxy_skip_address = 'http://skipittyskip'
    os.environ['http_proxy'] = 'http://foo'
    os.environ['https_proxy'] = 'http://bar'
    os.environ['no_proxy'] = proxy_skip_address

    proxy_settings = get_proxy()
    assert proxy_settings is not {}
    assert 'http' in proxy_settings
    assert proxy_settings['http'] == 'http://foo'
    assert 'https' in proxy_settings
    assert proxy_settings['https'] == 'http://bar'
    assert 'no_proxy' in proxy_settings
    assert 'no' not in proxy_settings

    no_proxy = proxy_settings['no_proxy'].split(',')
    assert proxy_skip_address in no_proxy
    for host in LOCAL_PROXY_SKIP:
        assert host in no_proxy

    os.environ.pop('http_proxy', None)
    os.environ.pop('https_proxy', None)
    os.environ.pop('no_proxy', None)


def test_https_proxy_precedence_dd_proxy_yaml_env():
    """DD_PROXY_HTTPS > proxy.https (yaml) > HTTPS_PROXY / getproxies()."""
    from config import config

    os.environ.pop('DD_PROXY_HTTPS', None)
    os.environ['HTTPS_PROXY'] = 'https://from-env-https'
    config.data['proxy'] = {'https': 'https://from-yaml'}

    p = get_proxy()
    assert p.get('https') == 'https://from-yaml'

    os.environ['DD_PROXY_HTTPS'] = 'https://from-dd'
    p = get_proxy()
    assert p.get('https') == 'https://from-dd'

    os.environ.pop('DD_PROXY_HTTPS')
    config.data.pop('proxy', None)
    p = get_proxy()
    assert p.get('https') == 'https://from-env-https'

    os.environ.pop('HTTPS_PROXY')


def test_no_proxy_yaml_overrides_no_proxy_env():
    """``proxy.no_proxy`` (yaml) wins over ``NO_PROXY`` / ``no_proxy`` when DD is unset."""
    from config import config

    config.data.pop('proxy', None)
    os.environ['no_proxy'] = 'from-env-only'
    os.environ.pop('NO_PROXY', None)
    os.environ.pop('DD_PROXY_NO_PROXY', None)

    config['proxy'] = {
        'http': 'http://dummy:8888',
        'https': 'http://dummy:8888',
        'no_proxy': ['.datadoghq.com', 'from-yaml-token'],
    }
    proxy_settings = get_proxy()
    assert 'datadoghq.com' in proxy_settings['no_proxy'] or '.datadoghq.com' in proxy_settings['no_proxy']
    assert 'from-yaml-token' in proxy_settings['no_proxy']
    assert 'from-env-only' not in proxy_settings['no_proxy']
    os.environ.pop('no_proxy', None)
    config.data.pop('proxy', None)


def test_dd_proxy_no_proxy_overrides_yaml_and_env():
    from config import config

    config.data.pop('proxy', None)
    os.environ['no_proxy'] = 'from-env-only'
    os.environ['DD_PROXY_NO_PROXY'] = 'from-dd-only'
    config['proxy'] = {
        'http': 'http://dummy:8888',
        'https': 'http://dummy:8888',
        'no_proxy': ['.datadoghq.com'],
    }
    proxy_settings = get_proxy()
    assert proxy_settings['no_proxy'].split(',')[0] == 'from-dd-only'
    assert 'datadoghq' not in proxy_settings['no_proxy']
    assert 'from-env-only' not in proxy_settings['no_proxy']
    os.environ.pop('no_proxy', None)
    os.environ.pop('DD_PROXY_NO_PROXY', None)
    config.data.pop('proxy', None)


def test_no_proxy_star_yaml_skips_local_proxy_skip():
    from config import config

    # Do not use config.reset('proxy'): prior tests may have removed the key.
    config.data.pop('proxy', None)
    for k in ('no_proxy', 'NO_PROXY', 'http_proxy', 'https_proxy'):
        os.environ.pop(k, None)

    config['proxy'] = {
        'http': 'http://dummy:8888',
        'https': 'http://dummy:8888',
        'no_proxy': ['*'],
    }
    proxy_settings = get_proxy()
    assert proxy_settings['no_proxy'] == '*'
    assert 'no' not in proxy_settings
    for host in LOCAL_PROXY_SKIP:
        assert host not in proxy_settings['no_proxy']


def test_should_bypass_proxy_leading_dot_subdomains_only():
    rules = ['.y.com']
    assert should_bypass_proxy('https://x.y.com/path', rules)
    assert not should_bypass_proxy('https://y.com/', rules)


def test_should_bypass_proxy_domain_matches_self_and_subdomains():
    rules = ['example.com']
    assert should_bypass_proxy('https://www.example.com/x', rules)
    assert should_bypass_proxy('https://example.com/', rules)
    assert not should_bypass_proxy('https://notexample.com/', rules)
    assert not should_bypass_proxy('https://example.org/', rules)


def test_should_bypass_proxy_wildcard_subdomain_prefix():
    rules = ['*.example.com']
    assert should_bypass_proxy('https://www.example.com/', rules)
    assert not should_bypass_proxy('https://example.com/', rules)


def test_should_bypass_proxy_star():
    assert should_bypass_proxy('https://any.host/', ['127.0.0.1', '*'])


def test_should_bypass_proxy_unix_scheme():
    assert should_bypass_proxy('unix:///var/run/docker.sock', ['127.0.0.1'])


def test_should_bypass_proxy_ip_cidr():
    rules = ['127.1.0.0/25']
    assert should_bypass_proxy('http://127.1.0.50/', rules)
    assert should_bypass_proxy('http://127.1.0.100/', rules)
    assert not should_bypass_proxy('http://127.1.0.150/', rules)


def test_should_bypass_proxy_empty_rules():
    assert not should_bypass_proxy('https://example.com/', [])


def test_no_proxy_yaml_string_not_split_on_commas():
    assert _no_proxy_yaml_tokens('a,b,c') == ['a,b,c']


def test_split_no_proxy_env_string():
    assert _split_no_proxy_env_string('a, b; c') == ['a', 'b', 'c']


def test_get_site():
    from config import config

    dd_url = config.get('dd_url')
    dd_site = get_site_url(dd_url, site=config.get('site'))
    assert dd_site == config.get('dd_url')

    dd_site = get_site_url(dd_url, site='datadoghq.eu')
    assert dd_site != config.get('dd_url')

    parsed_dd_url = urlparse(dd_url)
    parsed_dd_site = urlparse(dd_site)
    assert parsed_dd_site.netloc.split('.')[0:-2] == parsed_dd_url.netloc.split('.')[0:-2]
    assert parsed_dd_site.netloc.endswith('datadoghq.eu')
    assert parsed_dd_site.scheme == 'https'
