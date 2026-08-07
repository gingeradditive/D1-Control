# backend/dryer/components/fan.py
import time

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    print("[Fan] RPi.GPIO not available, running in simulation mode.")

class Fan:
    def __init__(self, gpio_pin: int = 24):
        self.gpio_pin = gpio_pin
        self._is_on = False
        if IS_RASPBERRY:
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)

    def on(self):
        if IS_RASPBERRY:
            # Defensive: re-force pin as OUTPUT in case it was reset
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            # Clean edge: ensure LOW before going HIGH
            GPIO.output(self.gpio_pin, GPIO.LOW)
            time.sleep(0.005)
            GPIO.output(self.gpio_pin, GPIO.HIGH)
            # Verify pin state
            state = GPIO.input(self.gpio_pin)
            if not state:
                print(f"[Fan] WARNING: GPIO {self.gpio_pin} read back LOW after setting HIGH!")
        self._is_on = True

    def off(self):
        if IS_RASPBERRY:
            GPIO.setup(self.gpio_pin, GPIO.OUT)
            GPIO.output(self.gpio_pin, GPIO.LOW)
        self._is_on = False

    def is_on(self) -> bool:
        return self._is_on

    def cleanup(self):
        if IS_RASPBERRY:
            GPIO.output(self.gpio_pin, GPIO.LOW)
