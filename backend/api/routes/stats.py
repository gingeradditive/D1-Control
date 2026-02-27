import os
import time
import platform
from fastapi import APIRouter
from backend.core.state import controllers

router = APIRouter()
dryer = controllers["dryer"]
_boot_time = time.time()


def _read_file(path, default=""):
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except Exception:
        return default


def _cpu_usage():
    try:
        with open("/proc/stat") as f:
            p1 = f.readline().split()
        idle1, total1 = int(p1[4]), sum(int(x) for x in p1[1:])
        time.sleep(0.1)
        with open("/proc/stat") as f:
            p2 = f.readline().split()
        idle2, total2 = int(p2[4]), sum(int(x) for x in p2[1:])
        dt = total2 - total1
        return round((1.0 - (idle2 - idle1) / dt) * 100, 1) if dt else 0.0
    except Exception:
        return None


def _memory():
    try:
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                parts = line.split()
                info[parts[0].rstrip(":")] = int(parts[1])
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        used = total - avail
        return {
            "total_mb": round(total / 1024, 1),
            "used_mb": round(used / 1024, 1),
            "available_mb": round(avail / 1024, 1),
            "percent": round(used / total * 100, 1) if total else 0,
        }
    except Exception:
        return None


def _cpu_temp():
    try:
        t = _read_file("/sys/class/thermal/thermal_zone0/temp")
        return round(int(t) / 1000.0, 1)
    except Exception:
        return None


def _disk():
    try:
        s = os.statvfs("/")
        total = s.f_blocks * s.f_frsize
        free = s.f_bfree * s.f_frsize
        used = total - free
        return {
            "total_gb": round(total / 1073741824, 2),
            "used_gb": round(used / 1073741824, 2),
            "free_gb": round(free / 1073741824, 2),
            "percent": round(used / total * 100, 1) if total else 0,
        }
    except Exception:
        return None


def _uptime():
    try:
        raw = _read_file("/proc/uptime")
        return round(float(raw.split()[0]), 0)
    except Exception:
        return round(time.time() - _boot_time, 0)


def _load_avg():
    try:
        raw = _read_file("/proc/loadavg")
        parts = raw.split()
        return {"1m": float(parts[0]), "5m": float(parts[1]), "15m": float(parts[2])}
    except Exception:
        return None


def _cpu_freq():
    try:
        raw = _read_file("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
        return round(int(raw) / 1000, 0)
    except Exception:
        return None


@router.get("")
def get_stats():
    hours = dryer.get_operating_hours()
    return {
        "dryer": {
            "partial_hours": hours["partial_hours"],
            "total_hours": hours["total_hours"],
            "filter_hours": hours["filter_hours"],
            "status": dryer.dryer_status,
        },
        "system": {
            "cpu_usage_percent": _cpu_usage(),
            "cpu_temp_c": _cpu_temp(),
            "cpu_freq_mhz": _cpu_freq(),
            "load_average": _load_avg(),
            "memory": _memory(),
            "disk": _disk(),
            "uptime_seconds": _uptime(),
            "platform": platform.machine(),
            "hostname": platform.node(),
        },
    }
