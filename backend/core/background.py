import sys
import time
import traceback


def background_loop(controllers, is_running):
    while is_running():
        dryer = controllers["dryer"]
        try:
            dryer.update_fan_cooldown()
            dryer.update_valve()
            now, temperature = dryer.read_sensor()
            dryer.update_heater(temperature)
            dryer.periodic_save_hours()

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
        time.sleep(1)
