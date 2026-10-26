# backend/dryer/components/valve.py
import time
import threading

from backend.dryer.components import gpio

IS_RASPBERRY = gpio.available()
if not IS_RASPBERRY:
    print("[Valve] GPIO not available, running in simulation mode.")

# Il servo è alimentato dalla stessa 5V del Pi: un salto unico di 90° assorbe
# un picco di corrente (e la corrente di stallo se arriva sul fermo meccanico)
# che sul campo ha mandato il Pi in brownout, con reset e ciclo interrotto.
# Muovendolo a piccoli passi il picco si riduce a quello di un passo.
RAMP_STEP_DEG = 5.0
RAMP_STEP_DELAY = 0.04  # s tra un passo e il successivo: 90° ≈ 0.7 s

# Dopo un movimento la 5V ha bisogno di qualche istante per riprendersi: in
# questa finestra il controller non commuta l'SSR del riscaldatore, così i
# due carichi non si sommano (vedi is_settling()).
SETTLE_TIME = 3.0  # s

DEFAULT_OPEN_ANGLE = 10.0
DEFAULT_CLOSED_ANGLE = 100.0


class Valve:
    """
    Valve controlled by a servo on a GPIO pin (lgpio).
    Provides open()/close() imitating original behavior.
    """
    def __init__(self, servo_pin: int = 17, disable_after: float = 0.3,
                 open_angle: float = DEFAULT_OPEN_ANGLE,
                 closed_angle: float = DEFAULT_CLOSED_ANGLE):
        self.servo_pin = servo_pin
        self.disable_after = disable_after
        self.open_angle = open_angle
        self.closed_angle = closed_angle
        self._is_open = False
        # posizione sconosciuta finché non comandiamo il primo movimento
        self._angle = None
        # ogni movimento incrementa la generazione: una rampa ancora in corso
        # vede il numero cambiato e si ferma, lasciando il posto alla nuova
        self._move_lock = threading.Lock()
        self._move_gen = 0
        self._move_thread = None
        self._last_move_end = None

    def _map_angle_to_pulse(self, angle: float) -> int:
        # 0-180 -> 500-2500 microseconds
        return int(500 + (angle / 180.0) * 2000)

    @staticmethod
    def _ramp(start, target, step=RAMP_STEP_DEG):
        """Angoli intermedi da start (escluso) a target (incluso)."""
        if start is None:
            # posizione ignota (primo comando dopo il boot): niente rampa possibile
            return [target]
        steps = []
        angle = start
        while abs(target - angle) > step:
            angle += step if target > angle else -step
            steps.append(angle)
        steps.append(target)
        return steps

    def _set_angle(self, angle: float):
        if not IS_RASPBERRY:
            # mock behavior
            print(f"[Valve MOCK] set_angle {angle}")
            self._angle = angle
            self._last_move_end = time.monotonic()
            return

        with self._move_lock:
            self._move_gen += 1
            gen = self._move_gen
            steps = self._ramp(self._angle, angle)
            # la rampa gira in un thread: il loop di controllo non deve
            # restare fermo per la durata del movimento
            self._move_thread = threading.Thread(
                target=self._run_ramp, args=(gen, steps), daemon=True, name="valve-ramp"
            )
            self._move_thread.start()

    def _run_ramp(self, gen: int, steps):
        try:
            for angle in steps:
                if gen != self._move_gen:
                    return
                gpio.servo(self.servo_pin, self._map_angle_to_pulse(angle))
                self._angle = angle
                time.sleep(RAMP_STEP_DELAY)
            # tiene la posizione un attimo, poi toglie l'impulso: il servo non
            # resta in tensione contro il fermo
            time.sleep(self.disable_after)
            if gen == self._move_gen:
                gpio.servo(self.servo_pin, 0)
        except Exception as e:
            print(f"[Valve] Servo move failed: {e}")
        finally:
            self._last_move_end = time.monotonic()

    def is_settling(self) -> bool:
        """True durante un movimento e per SETTLE_TIME secondi dopo."""
        if self._move_thread is not None and self._move_thread.is_alive():
            return True
        return self._last_move_end is not None and time.monotonic() - self._last_move_end < SETTLE_TIME

    def open(self):
        self._set_angle(self.open_angle)
        self._is_open = True

    def close(self):
        self._set_angle(self.closed_angle)
        self._is_open = False

    def is_open(self) -> bool:
        return self._is_open

    def cleanup(self):
        with self._move_lock:
            self._move_gen += 1  # interrompe una rampa in corso
        if self._move_thread is not None:
            self._move_thread.join(timeout=2)
        if IS_RASPBERRY:
            gpio.servo(self.servo_pin, 0)
            gpio.release(self.servo_pin)
