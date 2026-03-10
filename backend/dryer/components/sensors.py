# backend/dryer/components/sensors.py
import random
import time
from datetime import datetime
from typing import Tuple

try:
    import spidev
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    print("[Sensors] Hardware libraries not available, running in simulation mode.")


class Sensors:
    def __init__(self, max6675_bus=0, max6675_device=0):
        self.max6675_bus = max6675_bus
        self.max6675_device = max6675_device
        self.spi = None
        self._prev_temp = random.uniform(20, 30)

        if IS_RASPBERRY:
            try:
                self.spi = spidev.SpiDev()
                self.spi.open(self.max6675_bus, self.max6675_device)
                self.spi.max_speed_hz = 5000000
                self.spi.mode = 0b00
            except Exception as e:
                print(f"[Sensors] SPI init failed: {e}")
                self.spi = None

    def read_all(self) -> Tuple[datetime, float]:
        """Returns: (now, temperature)"""
        now = datetime.now()
        if IS_RASPBERRY:
            max6675_temp = 9999.0
            if self.spi:
                raw = self.spi.readbytes(2)
                if len(raw) == 2:
                    value = (raw[0] << 8) | raw[1]
                    if not value & 0x4:
                        max6675_temp = (value >> 3) * 0.25
            return now, max6675_temp
        else:
            self._prev_temp += random.uniform(-0.5, 0.5)
            self._prev_temp = max(15, min(70, self._prev_temp))
            if random.random() < 0.5:
                raise OSError("Simulated sensor read error")
            return now, self._prev_temp
