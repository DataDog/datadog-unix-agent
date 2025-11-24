# Licensed under Apache 2.0
# Datadog gohai-equivalent implementation in Python (AIX-safe)

import json
import platform
import socket
import subprocess
import psutil
import os


# --------------------------------------
# CPU Collector (AIX SAFE)
# --------------------------------------

def collect_cpu():
    info = {
        "cpu_cores": str(psutil.cpu_count(logical=True)),
        "model_name": "",
    }

    # Use psutil when possible (works everywhere)
    try:
        freq = psutil.cpu_freq()
        if freq:
            info["mhz"] = str(int(freq.max))
    except Exception:
        pass

    system = platform.system()

    # AIX has no /proc — use prtconf
    if system == "AIX":
        try:
            out = subprocess.check_output(["prtconf"], text=True, errors="ignore")
            for line in out.splitlines():
                line = line.strip()
                if "Processor Clock Speed" in line:
                    mhz = line.split(":")[1].strip().split(" ")[0]
                    info["mhz"] = mhz
                elif "Processor Type" in line:
                    info["model_name"] = line.split(":")[1].strip()
        except Exception:
            pass

        return info

    # Linux: optionally parse /proc/cpuinfo
    if os.path.exists("/proc/cpuinfo"):
        try:
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
        except Exception:
            pass

    # macOS / Windows fallback
    if not info["model_name"]:
        info["model_name"] = platform.processor()

    return info


# --------------------------------------
# Filesystem Collector
# --------------------------------------

def collect_filesystem():
    entries = []
    for part in psutil.disk_partitions(all=False):
        try:
            usage = psutil.disk_usage(part.mountpoint)
            entries.append({
                "name": part.device,
                "mounted_on": part.mountpoint,
                "kb_size": str(int(usage.total / 1024)),
            })
        except PermissionError:
            continue
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

def collect_network():
    addrs = psutil.net_if_addrs()

    result = {
        "ipaddress": "",
        "ipaddressv6": "",
        "macaddress": "",
    }

    for _, iface in addrs.items():
        for addr in iface:
            if addr.family == socket.AF_INET and not result["ipaddress"]:
                result["ipaddress"] = addr.address
            elif addr.family == socket.AF_INET6 and not result["ipaddressv6"]:
                result["ipaddressv6"] = addr.address
            elif addr.family == psutil.AF_LINK and not result["macaddress"]:
                result["macaddress"] = addr.address

    return result


# --------------------------------------
# Platform Collector
# --------------------------------------

def collect_platform():
    return {
        "GOOARCH": platform.machine(),
        "GOOS": platform.system().lower(),
        "hostname": socket.gethostname(),
        "kernel_name": platform.system(),
        "kernel_release": platform.release(),
        "kernel_version": platform.version(),
        "machine": platform.machine(),
        "os": platform.system(),
        "processor": platform.processor(),
        "pythonV": platform.python_version(),
        "goV": "",
    }


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
