# backend/dryer/components/heater.py
import time

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    print("[Heater] RPi.GPIO not available, running in simulation mode.")

class Heater:
    def __init__(self, gpio_pin: int = 23):
        self.gpio_pin = gpio_pin
        self._is_on = False
        if IS_RASPBERRY:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)

    def on(self):
        if IS_RASPBERRY:
            # Defensive: re-force pin as OUTPUT in case it was reset
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            # Clean edge: ensure LOW before going HIGH
            GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(0.05)
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            # Verify pin state
            state = GPIO.input(self.gpio_pin)
            if not state:
                print(f"[Heater] WARNING: GPIO {self.gpio_pin} read back LOW after setting HIGH!")
        self._is_on = True

    def off(self):
        if IS_RASPBERRY:
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)
        self._is_on = False

    def is_on(self) -> bool:
        return self._is_on

    def cleanup(self):
        pass
