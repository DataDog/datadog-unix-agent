# Licensed under Apache 2.0
# Datadog gohai-equivalent implementation in Python (AIX-safe)

import ipaddress
import json
import platform
import socket
import subprocess
import psutil
import os

from utils.platform import get_os, get_os_release


# Cached prtconf data so we only run it once
_prtconf_cache = None


def get_prtconf_info():
    """
    Run `prtconf` only once and extract:
        processor_type
        processor_clock_speed
        system_model
    """
    global _prtconf_cache
    if _prtconf_cache is not None:
        return _prtconf_cache

    data = {
        "processor_type": "",
        "processor_clock_speed": "",
        "system_model": ""
    }

    try:
        out = subprocess.check_output(
            ["prtconf"],
            text=True,
            errors="ignore"
        )
    except Exception:
        _prtconf_cache = data
        return data

    for line in out.splitlines():
        line = line.strip()

        if line.startswith("Processor Type:"):
            data["processor_type"] = line.split(":", 1)[1].strip()

        elif line.startswith("Processor Clock Speed:"):
            # Example: "Processor Clock Speed: 1000 MHz"
            parts = line.split(":", 1)[1].strip().split()
            if parts:
                data["processor_clock_speed"] = parts[0]  # "1000"

        elif line.startswith("System Model:"):
            data["system_model"] = line.split(":", 1)[1].strip()

    _prtconf_cache = data
    return data


# --------------------------------------
# CPU Collector
# --------------------------------------

def collect_cpu():
    # Gather everything we *might* include, then prune empty fields.
    info = {
        "cpu_cores": "",
        "cpu_logical_processors": "",
        "model_name": "",
        "mhz": "",
        "vendor_id": "",
        "cache_size": "",
        "family": "",
        "model": "",
        "stepping": ""
    }

    # --------------------------------------
    # Logical and physical CPU count
    # --------------------------------------
    try:
        logical = psutil.cpu_count(logical=True)
        physical = psutil.cpu_count(logical=False)
        info["cpu_logical_processors"] = str(logical or "")
        info["cpu_cores"] = str(physical or logical or "")
    except Exception:
        pass

    system = platform.system()

    # --------------------------------------
    # AIX CPU logic
    # --------------------------------------
    if system == "AIX":
        prt = get_prtconf_info()

        # Processor Type (PowerPC_POWER8, etc.)
        if prt.get("processor_type"):
            info["model_name"] = prt["processor_type"]

        # Processor Clock Speed (MHz)
        if prt.get("processor_clock_speed"):
            info["mhz"] = prt["processor_clock_speed"]

        # Vendor derived from model
        if info["model_name"]:
            info["vendor_id"] = info["model_name"].split("_")[0]

        # Remove fields that AIX will never populate
        aix_only_keep = ["cpu_cores", "cpu_logical_processors",
                         "model_name", "mhz", "vendor_id"]
        info = {k: v for k, v in info.items() if k in aix_only_keep and v}

        return info

    # --------------------------------------
    # Linux CPU collector
    # --------------------------------------
    if system == "Linux":
        try:
            if os.path.exists("/proc/cpuinfo"):
                with open("/proc/cpuinfo") as f:
                    for line in f:
                        k, _, v = line.partition(":")
                        k = k.strip().lower()
                        v = v.strip()

                        if k == "model name":
                            info["model_name"] = v
                        elif k == "vendor_id":
                            info["vendor_id"] = v
                        elif k == "cpu family":
                            info["family"] = v
                        elif k == "model":
                            info["model"] = v
                        elif k == "stepping":
                            info["stepping"] = v
                        elif k == "cpu mhz":
                            info["mhz"] = v.split(".")[0]
                        elif k == "cache size":
                            info["cache_size"] = v
        except Exception:
            pass

        # Prune only empty fields on Linux, but keep Linux-only fields if present
        info = {k: v for k, v in info.items() if v}

        return info

    # --------------------------------------
    # Unsupported OS
    # --------------------------------------
    return {}


# --------------------------------------
# Filesystem Collector
# --------------------------------------

def collect_filesystem():
    entries = []
    for part in psutil.disk_partitions(all=False):
        entry = {
            "name": part.device,
            "mounted_on": part.mountpoint,
        }

        kb_size = 0  # default to 0 if invalid

        try:
            usage = psutil.disk_usage(part.mountpoint)

            # If total is positive, compute KB. Otherwise, keep as 0.
            if usage.total > 0:
                kb_size = int(usage.total / 1024)

        except (PermissionError, FileNotFoundError, OSError):
            # On any error, kb_size stays 0
            pass

        # kb_size is always present and stringified
        entry["kb_size"] = str(kb_size)

        entries.append(entry)

    return entries


# --------------------------------------
# Memory Collector
# --------------------------------------

def collect_memory():
    vm = psutil.virtual_memory()
    sm = psutil.swap_memory()
    return {
        "total": str(vm.total),
        "swap_total": f"{sm.total/1024/1024:.2f}M",
    }


# --------------------------------------
# Network Collector
# --------------------------------------

def get_aix_mac_from_entstat(iface):
    try:
        out = subprocess.check_output(
            ["entstat", "-d", iface],
            text=True,
            stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if "Hardware Address:" in line:
                return line.split()[-1].strip()
    except Exception:
        pass
    return ""


def get_ipv4_netmask_from_lsattr(iface):
    try:
        out = subprocess.check_output(
            ["lsattr", "-El", iface],
            text=True,
            stderr=subprocess.DEVNULL
        )
        for line in out.splitlines():
            if line.strip().startswith("netmask"):
                parts = line.split()
                if len(parts) >= 2:
                    return parts[1].strip()
    except Exception:
        pass
    return ""


def is_loopback_iface(name, ipv4_list, ipv6_list):
    if name.lower() in ("lo", "lo0"):
        return True
    if any(ip.startswith("127.") for ip in ipv4_list):
        return True
    if "::1" in ipv6_list:
        return True
    return False


def collect_network():
    addrs = psutil.net_if_addrs()

    interfaces = []
    primary_ipv4 = ""
    primary_ipv6 = ""
    primary_mac = ""
    found_ipv6 = False  # Track existence of any IPv6

    for iface_name, iface_addrs in addrs.items():
        iface_ipv4 = []
        iface_ipv6 = []
        mac = ""

        ipv4_netmask = ""
        ipv6_network = ""  # Usually empty on AIX

        # Collect data via psutil
        for addr in iface_addrs:
            if addr.family == psutil.AF_LINK:
                mac = addr.address or ""

            elif addr.family == socket.AF_INET:
                iface_ipv4.append(addr.address)
                if addr.netmask:
                    ipv4_netmask = addr.netmask

            elif addr.family == socket.AF_INET6:
                iface_ipv6.append(addr.address)
                found_ipv6 = True  # A real IPv6 address exists somewhere

        # Remove loopback before further processing
        if is_loopback_iface(iface_name, iface_ipv4, iface_ipv6):
            continue

        # AIX netmask fallback
        if platform.system() == "AIX" and not ipv4_netmask and iface_ipv4:
            ipv4_netmask = get_ipv4_netmask_from_lsattr(iface_name)

        # AIX mac fallback
        if platform.system() == "AIX" and not mac:
            mac = get_aix_mac_from_entstat(iface_name)

        # Build interface entry
        iface_entry = {
            "name": iface_name,
            "macaddress": mac,
            "ipv4": iface_ipv4,
            "ipv4-network": ipv4_netmask,
        }

        # Add IPv6 ONLY if present
        if iface_ipv6:
            iface_entry["ipv6"] = iface_ipv6
        if iface_ipv6 and ipv6_network:
            iface_entry["ipv6-network"] = ipv6_network

        interfaces.append(iface_entry)

        # Primary selection
        if iface_ipv4 and not primary_ipv4:
            primary_ipv4 = iface_ipv4[0]
        if iface_ipv6 and not primary_ipv6:
            primary_ipv6 = iface_ipv6[0]
        if mac and not primary_mac:
            primary_mac = mac

    # Build final result
    network = {
        "interfaces": interfaces,
        "ipaddress": primary_ipv4,
        "macaddress": primary_mac,
    }

    # Add IPv6 ONLY if ANY was found globally
    if found_ipv6 and primary_ipv6:
        network["ipaddressv6"] = primary_ipv6

    return network


# --------------------------------------
# Platform Collector
# --------------------------------------

def collect_platform():
    system = get_os()

    plat = {
        "hostname": socket.gethostname(),
        "os": system,
        "machine": platform.machine(),
        "processor": platform.processor() or "",
        "pythonV": platform.python_version(),
        "hardware_platform": "",
        "kernel_version": platform.version(),   # placeholder
        "kernel_release": get_os_release()    # placeholder
    }

    # --------------------------------------
    # AIX logic
    # --------------------------------------
    if system.lower() == "aix":
        prt = get_prtconf_info()

        # Processor type from prtconf
        if prt.get("processor_type"):
            plat["processor"] = prt["processor_type"]

        # Hardware platform / system model
        if prt.get("system_model"):
            plat["hardware_platform"] = prt["system_model"]

        if not plat["hardware_platform"]:
            try:
                m = subprocess.check_output(
                    ["uname", "-M"], text=True, errors="ignore"
                ).strip()
                if m:
                    plat["hardware_platform"] = m
            except Exception:
                pass

        # kernel_version = major.minor (e.g. "7.2")
        try:
            major = subprocess.check_output(
                ["uname", "-v"], text=True, errors="ignore"
            ).strip()
            minor = subprocess.check_output(
                ["uname", "-r"], text=True, errors="ignore"
            ).strip()
            plat["kernel_version"] = major + "." + minor
        except Exception:
            plat["kernel_version"] = ""

        return plat

    # --------------------------------------
    # Linux logic
    # --------------------------------------
    if system == "Linux":
        # kernel_version = uname -v
        try:
            plat["kernel_version"] = subprocess.check_output(
                ["uname", "-v"], text=True, errors="ignore"
            ).strip()
        except Exception:
            pass

        # kernel_release = uname -r
        try:
            plat["kernel_release"] = subprocess.check_output(
                ["uname", "-r"], text=True, errors="ignore"
            ).strip()
        except Exception:
            pass

        plat["hardware_platform"] = plat["machine"]
        return plat

    # Other OS
    return plat


# --------------------------------------
# Top-level builder
# --------------------------------------

def collect_gohai():
    return {
        "cpu": collect_cpu(),
        "filesystem": collect_filesystem(),
        "memory": collect_memory(),
        "network": collect_network(),
        "platform": collect_platform(),
    }


# --------------------------------------
# Datadog-style Double-JSON Encoder
# --------------------------------------

def build_gohai_string():
    gohai_obj = collect_gohai()
    # Inner JSON is marshalled to a string, then that string is JSON encoded again.
    return json.dumps(gohai_obj)
