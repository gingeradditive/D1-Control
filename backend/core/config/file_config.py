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
    "pinned_preset_ids": ["pla", "petg"],
}


class FileConfig:
    """Gestione del file config.json.

    Lo stato vive in memoria (self._data) e il file è la sua copia
    persistita: get()/all() leggono dalla cache, set() scrive su disco solo
    quando il valore cambia davvero. Prima ogni get()/set() rileggeva e
    riscriveva l'intero JSON con fsync, inutile usura della SD dato che
    l'unico scrittore del file è questa stessa istanza.
    """

    def __init__(self, path: str = CONFIG_FILE, defaults: dict[str, Any] = None):
        self.path = path
        self.defaults = defaults or DEFAULT_CONFIG
        # Serializza le sequenze leggi->modifica->scrivi: os.replace() rende atomica
        # solo la sostituzione del file, non l'intera read-modify-write di set()/reset().
        self._lock = threading.Lock()
        # Se non esiste, crea il file con i valori di default
        if not os.path.exists(self.path):
            self._data = dict(self.defaults)
            self._write(self._data)
        else:
            self._data = self._read()
            self._migrate()

    def _migrate(self) -> None:
        """Integra una sola volta, all'avvio, le chiavi di default mancanti.
        Fuori da qui il file viene scritto solo su set()/reset()."""
        missing = {k: v for k, v in self.defaults.items() if k not in self._data}
        if missing:
            self._data.update(missing)
            self._write(self._data)

    def _read(self) -> dict[str, Any]:
        try:
            with open(self.path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            self._write(self.defaults)
            return dict(self.defaults)
        except Exception as e:
            print(f"[Config] Error reading {self.path}: {e}")
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
            print(f"[Config] Error saving {self.path}: {e}")
            if tmp_path:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def get(self, key: str, default: T, cast_type: Type[T] = str) -> T:
        """Legge una chiave dalla cache in memoria. Non modifica mai il file:
        una chiave assente ritorna il default senza essere persistita."""
        with self._lock:
            if key not in self._data:
                return default
            value = self._data[key]
        if value is None:
            return default
        try:
            return cast_type(value)
        except (ValueError, TypeError):
            print(f"[Config] Conversion failed for {key}, returning default: {default}")
            return default

    def set(self, key: str, value: Any) -> None:
        normalized = self._normalize(value)
        with self._lock:
            if key in self._data and self._data[key] == normalized:
                return  # nessuna modifica reale: salta la scrittura su disco
            self._data[key] = normalized
            self._write(self._data)

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
        with self._lock:
            return dict(self._data)

    def reset(self) -> None:
        """Elimina il file di configurazione e lo ricrea con i valori di default."""
        try:
            with self._lock:
                self._data = dict(self.defaults)
                if os.path.exists(self.path):
                    os.remove(self.path)
                self._write(self._data)
            print(f"[Config] {self.path} was reset to default values.")
        except Exception as e:
            print(f"[Config] Error resetting file {self.path}: {e}")
