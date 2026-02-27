import json
import os
from typing import TypeVar, Type, Any

CONFIG_FILE = "config.json"
T = TypeVar("T")

DEFAULT_CONFIG = {
    "heater_pulse_duration": 10,
    "heater_kp": 5.0,
    "heater_ki": 0.1,
    "heater_min_pause": 5,
    "heater_max_pause": 60,
    "setpoint": 70,
    "fan_cooldown_duration": 120,
    "valve_open_interval": 15,
    "valve_close_interval": 5,
    "inactivity_timeout": 5,
    "air_purge_time": 60,
    "drink_cycle_time": 3600,
    "screensaver_delay": 300,
}


class FileConfig:
    """Gestione del file config.json"""

    def __init__(self, path: str = CONFIG_FILE, defaults: dict[str, Any] = None):
        self.path = path
        self.defaults = defaults or DEFAULT_CONFIG
        # Se non esiste, crea il file con i valori di default
        if not os.path.exists(self.path):
            self._write(self.defaults)

    def _read(self) -> dict[str, Any]:
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            # Integra eventuali chiavi mancanti con i default
            updated = False
            for key, val in self.defaults.items():
                if key not in data:
                    data[key] = val
                    updated = True
            if updated:
                self._write(data)
            return data
        except (json.JSONDecodeError, FileNotFoundError):
            self._write(self.defaults)
            return dict(self.defaults)
        except Exception as e:
            print(f"[Config] Errore nel leggere {self.path}: {e}")
            return dict(self.defaults)

    def _write(self, data: dict[str, Any]) -> None:
        try:
            with open(self.path, "w") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"[Config] Errore nel salvare {self.path}: {e}")

    def get(self, key: str, default: T, cast_type: Type[T] = str) -> T:
        data = self._read()
        if key not in data:
            data[key] = default
            self._write(data)
            return default
        value = data[key]
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            print(f"[Config] Conversione fallita per {key}, ritorno default: {default}")
            return default

    def set(self, key: str, value: Any) -> None:
        data = self._read()
        data[key] = value
        self._write(data)

    def all(self) -> dict[str, Any]:
        return self._read()

    def reset(self) -> None:
        """Elimina il file di configurazione e lo ricrea con i valori di default."""
        try:
            if os.path.exists(self.path):
                os.remove(self.path)
            self._write(self.defaults)
            print(f"[Config] {self.path} è stato resettato ai valori di default.")
        except Exception as e:
            print(f"[Config] Errore nel reset del file {self.path}: {e}")
