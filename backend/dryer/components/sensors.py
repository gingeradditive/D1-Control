# backend/dryer/components/sensors.py
import random
import time
from datetime import datetime
from typing import Tuple

from backend.core.platform import IS_RASPBERRY as _ON_RASPBERRY

# Il solo successo dell'import non basta: su trixie python3-spidev arriva da
# apt anche dove non c'è un Raspberry (container di test, CI arm64), e senza
# SPI il sensore leggeva 9999 °C bloccando il dryer in sensor fault.
try:
    import spidev
    IS_RASPBERRY = _ON_RASPBERRY
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
if not IS_RASPBERRY:
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
                # MAX6675: clock massimo 4.3 MHz da datasheet. A 5 MHz (fuori
                # specifica) e con i disturbi dell'SSR sui cavi della termocoppia
                # le letture corrotte facevano scattare il fault sensore.
                self.spi.max_speed_hz = 1000000
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
                    if value & 0x4:
                        print(f"[Sensors] MAX6675 fault bit set — raw bytes: {raw!r} (0x{value:04x})")
                    else:
                        max6675_temp = (value >> 3) * 0.25
                else:
                    print(f"[Sensors] MAX6675 short read — expected 2 bytes, got: {raw!r}")
            return now, max6675_temp
        else:
            self._prev_temp += random.uniform(-0.5, 0.5)
            self._prev_temp = max(15, min(70, self._prev_temp))
            return now, self._prev_temp
