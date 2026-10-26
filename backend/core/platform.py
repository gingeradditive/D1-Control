# backend/core/platform.py
"""Rilevamento della piattaforma: prima si usava il successo di
`import RPi.GPIO`, libreria rimossa con il passaggio a lgpio (vedi
backend/dryer/components/gpio.py)."""


def _is_raspberry() -> bool:
    try:
        with open("/proc/device-tree/model") as f:
            return "Raspberry Pi" in f.read()
    except OSError:
        return False


IS_RASPBERRY = _is_raspberry()
