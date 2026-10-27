# backend/core/power.py
"""Stato dell'alimentazione letto dal firmware del Raspberry Pi.

Sul campo il ciclo si interrompeva perché la 5V scendeva sotto soglia (servo
della valvola, commutazioni dell'SSR) e il Pi andava in reset: nessun log,
journal volatile, dryer di nuovo spento al boot. Il firmware tiene traccia
degli eventi di sottotensione in un registro di bit; qui lo leggiamo e ne
logghiamo le variazioni nel journal. Volutamente niente avviso a schermo: il
problema è noto e il banner allarmava gli operatori senza dar loro modo di
intervenire.

Bit del registro (vedi `vcgencmd get_throttled`):
    0x1      sottotensione in corso
    0x4      throttling in corso
    0x10000  sottotensione avvenuta dall'ultimo boot
    0x40000  throttling avvenuto dall'ultimo boot
"""
import subprocess
from typing import Optional

UNDERVOLTAGE_NOW = 0x1
THROTTLED_NOW = 0x4
UNDERVOLTAGE_OCCURRED = 0x10000
THROTTLED_OCCURRED = 0x40000

_SYSFS_PATH = "/sys/devices/platform/soc/soc:firmware/get_throttled"


def read_throttled() -> Optional[int]:
    """Valore del registro, o None se non disponibile (non-Pi, sviluppo)."""
    try:
        with open(_SYSFS_PATH) as f:
            return int(f.read().strip(), 16)
    except (OSError, ValueError):
        pass
    try:
        out = subprocess.run(
            ["vcgencmd", "get_throttled"], capture_output=True, text=True, timeout=2
        ).stdout
        # "throttled=0x50005"
        return int(out.strip().split("=")[1], 16)
    except (OSError, IndexError, ValueError, subprocess.SubprocessError):
        return None


def describe(value: int) -> str:
    flags = []
    if value & UNDERVOLTAGE_NOW:
        flags.append("under-voltage now")
    if value & THROTTLED_NOW:
        flags.append("throttled now")
    if value & UNDERVOLTAGE_OCCURRED:
        flags.append("under-voltage since boot")
    if value & THROTTLED_OCCURRED:
        flags.append("throttling since boot")
    return f"0x{value:x} ({', '.join(flags) or 'ok'})"


class PowerMonitor:
    """Logga le variazioni del registro."""

    def __init__(self, reader=read_throttled):
        self._reader = reader
        self._last = None

    def check(self) -> Optional[int]:
        value = self._reader()
        if value is None or value == self._last:
            return value
        print(f"[Power] Throttling state changed: {describe(value)}")
        self._last = value
        return value
