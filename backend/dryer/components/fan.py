# backend/dryer/components/fan.py
from backend.dryer.components import gpio

IS_RASPBERRY = gpio.available()
if not IS_RASPBERRY:
    print("[Fan] GPIO not available, running in simulation mode.")

class Fan:
    def __init__(self, gpio_pin: int = 24):
        self.gpio_pin = gpio_pin
        self._is_on = False
        if IS_RASPBERRY:
            gpio.setup_output(self.gpio_pin, 0)

    def on(self):
        if IS_RASPBERRY:
            gpio.write(self.gpio_pin, 1)
            # Verify pin state
            if not gpio.read(self.gpio_pin):
                print(f"[Fan] WARNING: GPIO {self.gpio_pin} read back LOW after setting HIGH!")
        self._is_on = True

    def off(self):
        if IS_RASPBERRY:
            gpio.write(self.gpio_pin, 0)
        self._is_on = False

    def is_on(self) -> bool:
        return self._is_on

    def cleanup(self):
        if IS_RASPBERRY:
            gpio.release(self.gpio_pin)
