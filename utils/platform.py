# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import platform
import sys
import uuid


def get_os():
    "Human-friendly OS name"
    if sys.platform.find('freebsd') != -1:
        return 'freebsd'
    elif sys.platform.find('linux') != -1:
        return 'linux'
    elif sys.platform.find('sunos') != -1:
        return 'solaris'
    # TODO: add AIX
    else:
        return sys.platform

def get_uuid():
    # Generate a unique name that will stay constant between
    # invocations, such as platform.node() + uuid.getnode()
    # Use uuid5, which does not depend on the clock and is
    # recommended over uuid3.
    # This is important to be able to identify a server even if
    # its drives have been wiped clean.
    # Note that this is not foolproof but we can reconcile servers
    # on the back-end if need be, based on mac addresses.
    return uuid.uuid5(uuid.NAMESPACE_DNS, platform.node() + str(uuid.getnode())).hex

class Platform(object):
    """
    Return information about the given platform.
    """
    @staticmethod
    def is_freebsd():
        return sys.platform.startswith("freebsd")

    @staticmethod
    def is_linux():
        return 'linux' in sys.platform

    @staticmethod
    def is_solaris():
        return sys.platform == "sunos5"
