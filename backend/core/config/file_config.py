import json
import os
import tempfile
import threading
from typing import TypeVar, Type, Any

CONFIG_FILE = "config.json"
T = TypeVar("T")

DEFAULT_CONFIG = {
    "heater_on_duration": 10,
    "heater_off_duration": 5,
    "setpoint": 70,
    "fan_cooldown_duration": 120,
    "heater_hysteresis": 1.5,
    "purge_time": 1,
    "cycle_time": 60,
    "inactivity_timeout": 5,
    "screensaver_delay": 300,
    "pinned_preset_ids": ["pla", "petg"],
}


class FileConfig:
    """Gestione del file config.json"""

    def __init__(self, path: str = CONFIG_FILE, defaults: dict[str, Any] = None):
        self.path = path
        self.defaults = defaults or DEFAULT_CONFIG
        # Serializza le sequenze leggi->modifica->scrivi: os.replace() rende atomica
        # solo la sostituzione del file, non l'intera read-modify-write di set()/reset().
        self._lock = threading.Lock()
        # Se non esiste, crea il file con i valori di default
        if not os.path.exists(self.path):
            self._write(self.defaults)
        else:
            self._migrate()

    def _migrate(self) -> None:
        """Integra una sola volta, all'avvio, le chiavi di default mancanti.
        Fuori da qui il file viene scritto solo su set()/reset()."""
        data = self._read()
        missing = {k: v for k, v in self.defaults.items() if k not in data}
        if missing:
            data.update(missing)
            self._write(data)

    def _read(self) -> dict[str, Any]:
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._write(self.defaults)
            return dict(self.defaults)
        except Exception as e:
            print(f"[Config] Errore nel leggere {self.path}: {e}")
            return dict(self.defaults)

    def _write(self, data: dict[str, Any]) -> None:
        dir_ = os.path.dirname(os.path.abspath(self.path))
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as tmp:
                json.dump(data, tmp, indent=4)
                tmp.flush()
                os.fsync(tmp.fileno())
                tmp_path = tmp.name
            os.replace(tmp_path, self.path)
        except Exception as e:
            print(f"[Config] Errore nel salvare {self.path}: {e}")
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def get(self, key: str, default: T, cast_type: Type[T] = str) -> T:
        """Legge una chiave. Non modifica mai il file: una chiave assente
        ritorna il default senza essere persistita."""
        data = self._read()
        if key not in data:
            return default
        value = data[key]
        if value is None:
            return default
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            print(f"[Config] Conversione fallita per {key}, ritorno default: {default}")
            return default

    def set(self, key: str, value: Any) -> None:
        with self._lock:
            data = self._read()
            data[key] = self._normalize(value)
            self._write(data)

    @staticmethod
    def _normalize(value: Any) -> Any:
        """Coerce numeric-looking strings a int/float, cosi il tipo persistito
        non dipende da come il chiamante ha ottenuto il valore (es. form data)."""
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    pass
        return value

    def all(self) -> dict[str, Any]:
        return self._read()

    def reset(self) -> None:
        """Elimina il file di configurazione e lo ricrea con i valori di default."""
        try:
            with self._lock:
                if os.path.exists(self.path):
                    os.remove(self.path)
                self._write(self.defaults)
            print(f"[Config] {self.path} è stato resettato ai valori di default.")
        except Exception as e:
            print(f"[Config] Errore nel reset del file {self.path}: {e}")
