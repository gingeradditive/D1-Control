import sys
import time
import traceback


def background_loop(controllers, is_running):
    # Il battito iniziale è preso alla costruzione del controller, all'import:
    # se l'avvio di uvicorn è lento il watchdog vedrebbe un loop "fermo" prima
    # ancora della prima iterazione e fermerebbe il dryer (cancellando anche
    # l'avviso di riavvio imprevisto). Si riparte da adesso.
    controllers["dryer"].heartbeat()
    while is_running():
        dryer = controllers["dryer"]
        try:
            dryer.update_fan_cooldown()
            # La valvola non deve poter bloccare lettura sensore e riscaldatore:
            # un errore qui (es. GPIO occupato) faceva fallire ogni iterazione,
            # con temperatura congelata e riscaldatore spento a ciclo "acceso".
            try:
                dryer.update_valve()
            except Exception as e:
                print(f"[background_loop] Valve update failed: {e}", file=sys.stderr)
                dryer.errors.record(f"Valve error: {e}")
            now, temperature = dryer.read_sensor()
            dryer.update_heater(temperature)
            dryer.periodic_save_hours()
            dryer.update_power()

            if time.monotonic() - dryer.log_timer >= 10:
                dryer.log_timer = time.monotonic()
                dryer.log(now, temperature)
        except Exception:
            # The control loop must never die: a dead thread leaves the heater
            # latched in its last state and freezes the displayed temperature.
            print("[background_loop] Iteration failed:", file=sys.stderr)
            traceback.print_exc()
            try:
                dryer.heater.off()
            except Exception:
                pass
        finally:
            # Il thread è vivo anche se l'iterazione è fallita: il battito serve
            # a distinguere "loop bloccato" da "loop che sbaglia", e il secondo
            # caso ha già spento il riscaldatore qui sopra.
            dryer.heartbeat()
        time.sleep(1)
