# backend/core/watchdog.py
"""Deadman watchdog sul loop di controllo.

Il riscaldatore è comandato esclusivamente da `background_loop`. Se quel thread
smette di girare — deadlock, freeze, o semplicemente il thread che muore — l'SSR
resta agganciato all'ultimo stato comandato, potenzialmente **acceso**, a tempo
indefinito. Il try/except dentro il loop copre le eccezioni, non un blocco.

Due livelli indipendenti:

1. **software**: questo thread controlla il battito del loop e taglia il
   riscaldatore (e ferma il dryer) se il battito è più vecchio di
   `HEARTBEAT_TIMEOUT`.
2. **systemd**: finché il loop è vivo, mandiamo `WATCHDOG=1` al service manager
   (`WatchdogSec=` nell'unit). Se anche questo thread si ferma, systemd uccide e
   riavvia il processo, che rifà il setup GPIO con il pin LOW.
"""
import os
import socket
import sys
import threading
import time

# Età massima del battito del loop prima di considerarlo fermo.
# Il loop gira a 1 Hz: 5 s sono 5 iterazioni mancate.
HEARTBEAT_TIMEOUT = 5.0

# Ogni quanto il watchdog controlla il battito.
CHECK_INTERVAL = 1.0

_ERROR_KEY = "Control loop stalled — heater forced off by watchdog"


# --- notifica a systemd (sd_notify senza dipendenze esterne) ------------------

def sd_notify(state: str) -> bool:
    """Manda un messaggio al service manager. No-op fuori da systemd."""
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return False
    if addr.startswith("@"):  # abstract namespace
        addr = "\0" + addr[1:]
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sock:
            sock.connect(addr)
            sock.sendall(state.encode())
        return True
    except OSError as e:
        print(f"[watchdog] sd_notify fallita: {e}", file=sys.stderr)
        return False


def sd_watchdog_interval() -> float:
    """Intervallo di ping richiesto da systemd (metà di WatchdogSec), 0 se assente."""
    usec = os.environ.get("WATCHDOG_USEC")
    if not usec:
        return 0.0
    try:
        return max(int(usec) / 2_000_000.0, 1.0)
    except ValueError:
        return 0.0


class ControlLoopWatchdog(threading.Thread):
    def __init__(self, controllers, is_running, timeout: float = HEARTBEAT_TIMEOUT):
        super().__init__(daemon=True, name="control-loop-watchdog")
        self.controllers = controllers
        self.is_running = is_running
        self.timeout = timeout
        self.tripped = False
        self._ping_interval = sd_watchdog_interval()
        self._last_ping = 0.0

    def run(self):
        while self.is_running():
            try:
                self._check()
            except Exception as e:
                # Il watchdog non può morire: è l'ultima rete di sicurezza.
                print(f"[watchdog] Errore nel controllo: {e}", file=sys.stderr)
            time.sleep(CHECK_INTERVAL)

    def _check(self):
        dryer = self.controllers["dryer"]
        age = dryer.loop_heartbeat_age()

        if age > self.timeout:
            self._trip(dryer, age)
            return

        if self.tripped:
            self.tripped = False
            dryer.errors.pop(_ERROR_KEY, None)
            print("[watchdog] Loop di controllo ripartito.")

        self._ping_systemd()

    def _trip(self, dryer, age: float):
        # Il taglio va ripetuto ad ogni giro: se il loop è bloccato *dentro*
        # update_heater potrebbe riaccendere il pin dopo di noi.
        try:
            dryer.heater.off()
        except Exception as e:
            print(f"[watchdog] Impossibile spegnere il riscaldatore: {e}", file=sys.stderr)

        if self.tripped:
            return

        self.tripped = True
        dryer.errors.record(_ERROR_KEY, sticky=True)
        print(
            f"[watchdog] LOOP FERMO da {age:.1f}s — riscaldatore spento d'ufficio.",
            file=sys.stderr,
        )
        # Da qui in poi smettiamo di pingare systemd: se la situazione non si
        # risolve, il service manager riavvia il processo.
        try:
            dryer.stop()
        except Exception as e:
            print(f"[watchdog] stop() fallita: {e}", file=sys.stderr)

    def _ping_systemd(self):
        if not self._ping_interval:
            return
        now = time.monotonic()
        if now - self._last_ping >= self._ping_interval:
            self._last_ping = now
            sd_notify("WATCHDOG=1")
