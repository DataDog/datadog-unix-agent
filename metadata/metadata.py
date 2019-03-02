# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import platform
import psutil
import uuid
import socket
import sys
import time

from utils.platform import Platform, get_os
from config import config


def get_common(hostname):
    return {
        "agentVersion": "0.99.99", # fake one for now
        "apiKey": config.get("api_key"),
        "uuid": uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() + str(uuid.getnode())).hex,
        "internalHostname": hostname,
    }

def get_system_stats():
    system_stats = {
        "machine": platform.machine(),
        "platform": sys.platform,
        "processor": platform.processor(),
        "pythonV": platform.python_version(),
        "cpuCores": psutil.cpu_count(),
    }

    if Platform.is_linux():
        system_stats["nixV"] = platform.dist()
    elif Platform.is_freebsd():
        version = platform.uname()[2]
        system_stats['fbsdV'] = ('freebsd', version, '')  # no codename for FreeBSD
    return system_stats

def get_meta(hostname):
    return {
        "socket-hostname": socket.gethostname(),
        "timezones": time.tzname,
        "host_aliases": [], # cloud provider aliases
        "socket-fqdn": socket.getfqdn(),
        "hostname": hostname,
    }

def get_host_tags():
    return {
        "system": config.get("tags"),
    }

def get_host_metadata(hostname):
    return {
        "os": get_os(),
        "python": sys.version,
        "systemStats": get_system_stats(),
        "meta": get_meta(hostname),
        "host-tags": get_host_tags(),
    }

def get_resources(hostname):
    return {
        "meta": {"host": hostname},
        "processes": {"snaps": []},
    }

def get_metadata(hostname, start_event=False):
    metadata = get_common(hostname)
    metadata.update(get_host_metadata(hostname))
    metadata["resources"] = get_resources(hostname)
    metadata["events"] = {}
    if start_event:
        # Also post an event in the newsfeed
        metadata['events'].update({
            'System': [{
                'api_key': config.get('api_key'),
                'host': hostname,
                'timestamp': time.time(),
                'event_type':'Agent Startup',
                'msg_text': 'Version {}'.format('0.99.99')  # implement get_version()
            }]
        })
    return metadata
