# backend/dryer/components/valve.py
import time
import threading

try:
    import pigpio
    IS_RASPBERRY = True
except Exception:
    IS_RASPBERRY = False
    print("[Valve] pigpio not available, running in simulation mode.")

class Valve:
    """
    Valve controlled by a servo on a pigpio instance.
    Provides open()/close() imitating original behavior.
    """
    def __init__(self, servo_pin: int = 17, disable_after: float = 0.3):
        self.servo_pin = servo_pin
        self.disable_after = disable_after
        self._is_open = False
        self._pi = None
        self._pending_timers: set[threading.Timer] = set()
        if IS_RASPBERRY:
            self._pi = pigpio.pi()
            # no explicit set here; controller can call set_pulse when needed
            if not self._pi.connected:
                print("[Valve] WARNING: pigpiod is not running or unreachable — the valve will not move.")

    def _map_angle_to_pulse(self, angle: float) -> int:
        # 0-180 -> 500-2500 microseconds
        return int(500 + (angle / 180.0) * 2000)

    def _set_angle(self, angle: float):
        pulse = self._map_angle_to_pulse(angle)
        if IS_RASPBERRY and self._pi:
            if not self._pi.connected:
                print(f"[Valve] WARNING: pigpiod not connected, cannot set angle {angle}")
                return
            self._pi.set_servo_pulsewidth(self.servo_pin, pulse)
            # disable servo after small delay
            timer = threading.Timer(self.disable_after, self._disable_pulse)
            self._pending_timers.add(timer)
            timer.start()
        else:
            # mock behavior
            print(f"[Valve MOCK] set_angle {angle}")

    def _disable_pulse(self):
        self._pending_timers.discard(threading.current_thread())
        if self._pi and self._pi.connected:
            self._pi.set_servo_pulsewidth(self.servo_pin, 0)

    def open(self):
        # in original: set_angle(10)
        self._set_angle(10)
        self._is_open = True

    def close(self):
        # in original: set_angle(100)
        self._set_angle(100)
        self._is_open = False

    def is_open(self) -> bool:
        return self._is_open

    def cleanup(self):
        for timer in list(self._pending_timers):
            timer.cancel()
        self._pending_timers.clear()
        if IS_RASPBERRY and self._pi:
            if self._pi.connected:
                self._pi.set_servo_pulsewidth(self.servo_pin, 0)
            self._pi.stop()
