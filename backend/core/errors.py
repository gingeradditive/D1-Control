# backend/core/errors.py
"""Registro degli errori attivi esposti da `GET /status`.

Prima era un semplice `dict[str, str]` con chiave = testo dell'eccezione: ogni
messaggio distinto (e quelli del sensore contengono la temperatura, quindi sono
quasi sempre distinti) aggiungeva una voce che non veniva mai rimossa, e l'intero
dizionario veniva serializzato una volta al secondo.

Qui il registro è limitato in due modi:

* **TTL**: una voce transitoria scade `ttl` secondi dopo l'ultima occorrenza.
  Le voci *sticky* (fault sensore, watchdog) rappresentano una condizione
  persistente e vengono rimosse solo da chi le ha inserite, con `pop()`.
* **Tetto massimo**: oltre `max_entries` voci si scarta la più vecchia,
  preferendo sempre una transitoria a una sticky.

Il registro è scritto dal loop di controllo e dal thread del watchdog e letto
dai worker FastAPI, quindi ogni operazione è sotto lock.
"""
import threading
import time
from collections import OrderedDict
from datetime import datetime
from typing import Dict, Optional

# Un errore transitorio sparisce da solo dopo questo tempo dall'ultima occorrenza.
DEFAULT_TTL = 600.0  # 10 minuti

# Tetto rigido sul numero di voci simultanee.
DEFAULT_MAX_ENTRIES = 20


class _Entry:
    __slots__ = ("timestamp", "sticky", "last_seen")

    def __init__(self, timestamp: str, sticky: bool):
        self.timestamp = timestamp      # ISO della *prima* occorrenza
        self.sticky = sticky
        self.last_seen = time.monotonic()


class ErrorRegistry:
    def __init__(self, ttl: float = DEFAULT_TTL, max_entries: int = DEFAULT_MAX_ENTRIES):
        self._ttl = ttl
        self._max_entries = max_entries
        self._entries: "OrderedDict[str, _Entry]" = OrderedDict()
        self._lock = threading.Lock()

    # --- scrittura ---
    def record(self, key: str, sticky: bool = False, when: Optional[datetime] = None) -> None:
        """Registra un errore attivo.

        Se la chiave è già presente ne rinfresca la scadenza ma **non** il
        timestamp: la UI usa `descrizione + data` come identità del toast, e
        cambiarla ad ogni occorrenza ne farebbe comparire uno nuovo al secondo.
        """
        with self._lock:
            self._expire_locked()
            entry = self._entries.get(key)
            if entry is not None:
                entry.last_seen = time.monotonic()
                entry.sticky = entry.sticky or sticky
                return
            self._entries[key] = _Entry((when or datetime.now()).isoformat(), sticky)
            self._evict_locked()

    def pop(self, key: str, default=None):
        with self._lock:
            entry = self._entries.pop(key, None)
            return default if entry is None else entry.timestamp

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    # --- lettura ---
    def snapshot(self) -> Dict[str, str]:
        """Copia serializzabile `{descrizione: data ISO}` per `GET /status`."""
        with self._lock:
            self._expire_locked()
            return {key: entry.timestamp for key, entry in self._entries.items()}

    def __contains__(self, key: str) -> bool:
        with self._lock:
            self._expire_locked()
            return key in self._entries

    def __len__(self) -> int:
        with self._lock:
            self._expire_locked()
            return len(self._entries)

    # --- interni (chiamati con il lock già preso) ---
    def _expire_locked(self) -> None:
        if self._ttl <= 0:
            return
        now = time.monotonic()
        for key in [
            k for k, e in self._entries.items()
            if not e.sticky and now - e.last_seen > self._ttl
        ]:
            del self._entries[key]

    def _evict_locked(self) -> None:
        while len(self._entries) > self._max_entries:
            victim = next(
                (k for k, e in self._entries.items() if not e.sticky),
                next(iter(self._entries)),
            )
            del self._entries[victim]
