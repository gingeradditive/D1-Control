# backend/dryer/components/gpio.py
"""Accesso ai GPIO tramite lgpio (character device del kernel).

Sostituisce RPi.GPIO e pigpio: RPi.GPIO non supporta il Pi 5 e pigpio non è
più distribuito con Raspberry Pi OS trixie; inoltre pigpio richiedeva il
demone pigpiod, un processo in più che poteva cadere lasciando la valvola
ferma. lgpio funziona su bookworm e trixie, Pi 3/4/5, senza demoni.

Fuori da un Raspberry (sviluppo, CI) `available()` è False e i componenti
girano in simulazione.
"""
import threading

try:
    import lgpio
except (ImportError, OSError):
    lgpio = None

# Sul Pi 5 con kernel recenti il connettore a 40 pin è gpiochip0 come sugli
# altri modelli; con kernel più vecchi era gpiochip4.
_CHIP_CANDIDATES = (0, 4)

_lock = threading.Lock()
_handle = None
_claimed = set()


def _open_chip():
    global _handle
    if _handle is not None or lgpio is None:
        return _handle
    for chip in _CHIP_CANDIDATES:
        try:
            handle = lgpio.gpiochip_open(chip)
        except lgpio.error:
            continue
        # il chip giusto è quello che espone le linee del connettore (>= 28)
        try:
            if lgpio.gpio_get_chip_info(handle)[1] >= 28:
                _handle = handle
                return _handle
        except lgpio.error:
            pass
        lgpio.gpiochip_close(handle)
    print("[GPIO] No usable gpiochip found, running in simulation mode.")
    return None


def available() -> bool:
    with _lock:
        return _open_chip() is not None


def setup_output(pin: int, level: int = 0) -> None:
    with _lock:
        handle = _open_chip()
        if handle is None:
            return
        lgpio.gpio_claim_output(handle, pin, level)
        _claimed.add(pin)


def write(pin: int, level: int) -> None:
    with _lock:
        if _handle is None:
            return
        if pin not in _claimed:
            lgpio.gpio_claim_output(_handle, pin, level)
            _claimed.add(pin)
        else:
            lgpio.gpio_write(_handle, pin, level)


def read(pin: int) -> int:
    with _lock:
        if _handle is None:
            return 0
        return lgpio.gpio_read(_handle, pin)


def servo(pin: int, pulse_width_us: int) -> None:
    """Impulso servo a 50 Hz; 0 spegne l'impulso."""
    with _lock:
        if _handle is None:
            return
        if pin not in _claimed:
            lgpio.gpio_claim_output(_handle, pin, 0)
            _claimed.add(pin)
        lgpio.tx_servo(_handle, pin, pulse_width_us)


def release(pin: int) -> None:
    """Porta il pin a LOW e lo rilascia."""
    with _lock:
        if _handle is None or pin not in _claimed:
            return
        try:
            lgpio.gpio_write(_handle, pin, 0)
            lgpio.gpio_free(_handle, pin)
        finally:
            _claimed.discard(pin)


def cleanup() -> None:
    global _handle
    with _lock:
        if _handle is None:
            return
        for pin in list(_claimed):
            try:
                lgpio.gpio_write(_handle, pin, 0)
                lgpio.gpio_free(_handle, pin)
            except lgpio.error:
                pass
        _claimed.clear()
        lgpio.gpiochip_close(_handle)
        _handle = None
