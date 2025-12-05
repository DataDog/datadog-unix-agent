# Unless explicitly stated otherwise all files in this repository are licensed
# under the Apache License Version 2.0.
# This product includes software developed at Datadog (https://www.datadoghq.com/).
# Copyright 2018 Datadog, Inc.

import os
import platform
import subprocess
import sys
import uuid

OS_PLATFORM = sys.platform


def get_os():
    "Human-friendly OS name"
    if OS_PLATFORM.find('freebsd') != -1:
        return 'freebsd'
    elif OS_PLATFORM.find('linux') != -1:
        return 'linux'
    elif OS_PLATFORM.find('sunos') != -1:
        return 'solaris'
    elif OS_PLATFORM.startswith('aix'):
        return 'aix'
    else:
        return OS_PLATFORM


def get_aix_oslevel():
    """
    Return the full AIX OS level (example: 7200-04-02-2027).
    Uses oslevel -s and ignores rpmdb errors printed to stderr.
    If not on AIX, return empty string.
    """
    if not OS_PLATFORM.startswith("aix"):
        return ""

    try:
        out = subprocess.check_output(
            ["oslevel", "-s"],
            text=True,
            stderr=subprocess.DEVNULL
        )
        for line in reversed(out.splitlines()):
            line = line.strip()
            # Expected format ####-##-##-####
            if "-" in line and len(line) >= 10:
                return line
    except Exception:
        pass

    return ""


def get_os_release():
    """
    Return OS release suitable for display.
    On AIX: oslevel -s (full OS/TL/SP/build).
    On Linux: platform.release().
    """
    if OS_PLATFORM.startswith("aix"):
        lvl = get_aix_oslevel()
        return lvl or platform.release()

    return platform.release()


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


def running_root():
    return os.getuid() == 0


class Platform(object):
    """
    Return information about the given platform.
    """
    @staticmethod
    def is_freebsd():
        return OS_PLATFORM.startswith("freebsd")

    @staticmethod
    def is_linux():
        return 'linux' in OS_PLATFORM

    @staticmethod
    def is_solaris():
        return OS_PLATFORM == "sunos5"

    @staticmethod
    def is_aix():
        return OS_PLATFORM.startswith('aix')
