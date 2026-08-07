# backend/dryer/controller.py
import glob
import os
import time
from datetime import datetime, timedelta
from collections import deque
import sys

from backend.dryer.components.heater import Heater
from backend.dryer.components.fan import Fan
from backend.dryer.components.valve import Valve
from backend.dryer.components.sensors import Sensors
from backend.core.errors import ErrorRegistry

# Sensor validity range — outside these bounds the reading is treated as a fault.
# The MAX6675 returns 9999.0 on open-thermocouple; 0.0 on a shorted/disconnected probe.
SENSOR_TEMP_MIN = 5.0    # °C — below this the probe is disconnected or shorted
SENSOR_TEMP_MAX = 300.0  # °C — above this the probe is disconnected or the MAX6675 fault bit is set

# Cutoff di processo assoluto, indipendente dal setpoint (max consentito 90°C,
# vedi backend/core/constants.py): SENSOR_TEMP_MAX è una soglia di guasto
# sensore, non un limite di sicurezza — un setpoint sbagliato o un controllo
# fuori scala non verrebbero mai fermati da quella sola. Spegne comunque il
# riscaldatore, indipendentemente dal setpoint impostato.
PROCESS_TEMP_HARD_CUTOFF = 95.0  # °C
_HARD_CUTOFF_KEY = "Hard safety cutoff: temperature above process limit"

# Consecutive bad readings before entering fault state, and consecutive good readings to exit it.
_FAULT_TRIP_COUNT  = 3
_FAULT_CLEAR_COUNT = 5

_LOG_MAX_FILES = 30

# "Riscalda ma non sale": se la termocoppia si sfila, l'SSR si guasta aperto o
# la resistenza si brucia, il riscaldatore resta ON senza che la temperatura
# salga. Controllo sulla derivata: riscaldatore ON per N minuti con ΔT < soglia.
_HEAT_STALL_MINUTES = 10
_HEAT_STALL_MIN_DELTA = 2.0  # °C attesi in finestra
_HEAT_STALL_KEY = "Heating stalled: heater ON but temperature not rising"

_UNEXPECTED_RESTART_KEY = "Previous drying cycle was interrupted by an unexpected restart"


class DryerController:
    def __init__(self, config):
        self.config = config

        # heater pulse config
        self.heater_on_duration = self.config.get("heater_on_duration", 10, int)
        self.heater_off_duration = self.config.get("heater_off_duration", 5, int)

        # setpoint
        set_temp = self.config.get("setpoint", 70, int)
        self.set_temp = set_temp
        # Isteresi assoluta (°C), non proporzionale al setpoint: allo 0.5% del
        # MAX6675 (risoluzione 0.25 °C) un'isteresi relativa cicla sul rumore
        # del sensore a bassi setpoint.
        self.tolerance = self.config.get("heater_hysteresis", 1.5, float)

        # fan cooldown
        self.fan_cooldown_duration = self.config.get("fan_cooldown_duration", 120, int)

        # purge / cycle
        self.purge_time = self.config.get("purge_time", 1, int)
        self.cycle_time = self.config.get("cycle_time", 60, int)

        # state  (all elapsed timers use monotonic to survive NTP jumps on RPi)
        self.last_heater_toggle = time.monotonic()
        self.history = deque(maxlen=43200)
        self.log_timer = time.monotonic()
        self.dryer_status = False
        self.fan_cooldown_end = None
        self.cooldown_active = False
        self.valve_last_switch_time = time.monotonic()

        # media mobile sulle letture valide: il MAX6675 converte in ~220ms ed è
        # letto a 1Hz, il campione grezzo è rumoroso. Il filtro agisce solo sul
        # valore usato per storia/controllo/UI, non sulla validazione del fault
        # (quella resta sul campione grezzo, per reagire subito a un'anomalia).
        self._temp_filter = deque(maxlen=4)

        # deadman heartbeat: aggiornato ad ogni iterazione del loop di controllo,
        # sorvegliato da ControlLoopWatchdog (backend/core/watchdog.py)
        self._last_loop_beat = time.monotonic()
        # ultima lettura sensore valida, per /api/health
        self._last_sensor_read = None

        # operating hours
        self.total_hours = self.config.get("total_operating_hours", 0.0, float)
        self.filter_hours = self.config.get("filter_operating_hours", 0.0, float)
        self.session_start_time = None
        self._hours_save_timer = time.monotonic()

        # registro errori limitato (TTL + tetto massimo): vedi backend/core/errors.py
        self.errors = ErrorRegistry()

        # "acceso" non persistente: se il processo precedente si è fermato
        # mentre il dryer era in funzione (crash, OOM, riavvio imprevisto),
        # avvisa l'operatore invece di ripartire spento in silenzio.
        if self.config.get("was_running", False, bool):
            self.errors.record(_UNEXPECTED_RESTART_KEY, sticky=True)
            print("[DryerController] Previous session was interrupted by an unexpected restart.")

        # rilevamento "riscalda ma non sale": vedi _HEAT_STALL_* sotto
        self._heat_stall_baseline = None

        # sensor fault tracking
        self.sensor_fault = False
        # descrizione del fault attivo: è anche la chiave usata in self.errors,
        # serve per ripulirla quando il fault rientra
        self.sensor_fault_desc = None
        self._sensor_bad_streak  = 0
        self._sensor_good_streak = 0

        # components — GPIO mode must be set once before any component setup
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
        except (ImportError, NotImplementedError):
            pass
        self.heater = Heater()
        self.fan = Fan()
        self.valve = Valve()
        self.sensors = Sensors()

        # log file — created lazily on first log() call to avoid a wrong date
        # if NTP hasn't synced yet at boot time
        self.log_file = None
        self._log_date = None

        # ripopola la history in RAM dal CSV di oggi, cosi' i grafici non
        # ripartono vuoti ad ogni riavvio del servizio. Risoluzione più bassa
        # (10s, contro l'1Hz della history live), best-effort: un file
        # mancante o corrotto non deve mai impedire l'avvio.
        self._load_history_from_csv()

    def _load_history_from_csv(self):
        log_file = f"logs/temperature_{datetime.now().strftime('%Y-%m-%d')}.csv"
        if not os.path.exists(log_file):
            return
        try:
            with open(log_file, "r") as f:
                lines = f.readlines()
        except Exception as e:
            print(f"[DryerController] Cannot read {log_file} for history reload: {e}")
            return

        loaded = 0
        for line in lines[1:]:  # skip header
            parts = line.strip().split(";")
            if len(parts) != 6:
                continue
            try:
                ts = datetime.strptime(parts[0], "%Y-%m-%d %H:%M:%S")
                temp = float(parts[1])
                heater_on = bool(int(parts[2]))
                fan_on = bool(int(parts[3]))
                # parts[4] è il setpoint, non presente nella tupla di history
                valve_open = bool(int(parts[5]))
            except (ValueError, IndexError):
                continue
            self.history.append((ts, temp, heater_on, fan_on, valve_open))
            loaded += 1

        if loaded:
            print(f"[DryerController] Reloaded {loaded} history points from {log_file}")

    # --- deadman heartbeat ---
    def heartbeat(self):
        """Segnala che il loop di controllo ha completato un'iterazione."""
        self._last_loop_beat = time.monotonic()

    def loop_heartbeat_age(self) -> float:
        return time.monotonic() - self._last_loop_beat

    def sensor_reading_age(self) -> float:
        """Secondi dall'ultima lettura sensore valida, o inf se non ancora avvenuta."""
        if self._last_sensor_read is None:
            return float("inf")
        return time.monotonic() - self._last_sensor_read

    # --- start / stop ---
    def start(self):
        if self.sensor_fault:
            print("[DryerController] Start blocked: sensor fault active.", file=sys.stderr)
            return False
        self.errors.pop(_UNEXPECTED_RESTART_KEY, None)
        if not self.dryer_status:
            self.dryer_status = True
            self.cooldown_active = False
            self.fan_cooldown_end = None
            self.session_start_time = time.monotonic()
            self.fan.on()
            self.valve.close()
            self.valve_last_switch_time = time.monotonic()
            self.last_heater_toggle = time.monotonic()
            self.config.set("was_running", True)
            print("Dryer started.")
        return True

    def stop(self):
        # Va ripulito anche se dryer_status è già False: un riavvio spegne il
        # dryer senza passare da qui, e l'operatore deve poter riconoscere
        # l'avviso di riavvio imprevisto fermando esplicitamente il ciclo.
        self.config.set("was_running", False)
        self.errors.pop(_UNEXPECTED_RESTART_KEY, None)
        if self.dryer_status:
            self._accumulate_session_hours()
            self.dryer_status = False
            self.heater.off()
            print("Dryer stopped.")
            self.fan_cooldown_end = time.monotonic() + self.fan_cooldown_duration
            self.cooldown_active = True
            self.valve.close()
            print("Fan cooldown started.")

    # --- properties ---
    @property
    def ssr_heater(self):
        return self.heater.is_on()

    @property
    def ssr_fan(self):
        return self.fan.is_on()

    @property
    def valve_is_open(self):
        return self.valve.is_open()

    # --- sensor read ---
    def _is_temp_valid(self, temp: float) -> bool:
        return SENSOR_TEMP_MIN <= temp <= SENSOR_TEMP_MAX

    def read_sensor(self):
        now = datetime.now()
        temperature = None

        try:
            now, temperature = self.sensors.read_all()
        except Exception as e:
            print(f"Sensor read error: {e}", file=sys.stderr)
            self.errors.record(str(e), when=now)

        valid = temperature is not None and self._is_temp_valid(temperature)

        if valid:
            self._sensor_bad_streak = 0
            self._sensor_good_streak = min(self._sensor_good_streak + 1, _FAULT_CLEAR_COUNT)

            if self.sensor_fault:
                if self._sensor_good_streak >= _FAULT_CLEAR_COUNT:
                    self.sensor_fault = False
                    if self.sensor_fault_desc is not None:
                        self.errors.pop(self.sensor_fault_desc, None)
                        self.sensor_fault_desc = None
                    print("[DryerController] Sensor fault cleared — readings back to normal.")

            self._temp_filter.append(temperature)
            filtered_temp = sum(self._temp_filter) / len(self._temp_filter)

            self._last_sensor_read = time.monotonic()
            self.history.append((now, filtered_temp, self.ssr_heater, self.ssr_fan, self.valve_is_open))
            return now, filtered_temp

        # --- invalid reading ---
        self._sensor_good_streak = 0
        self._sensor_bad_streak += 1

        if temperature is None:
            fault_desc = "Sensor communication error"
        elif temperature <= 0:
            fault_desc = f"Temperature is {temperature:.1f}°C — probe shorted or disconnected"
        elif temperature < SENSOR_TEMP_MIN:
            fault_desc = f"Temperature too low: {temperature:.1f}°C (min {SENSOR_TEMP_MIN}°C)"
        else:
            fault_desc = f"Temperature too high: {temperature:.1f}°C (max {SENSOR_TEMP_MAX}°C)"

        if not self.sensor_fault and self._sensor_bad_streak >= _FAULT_TRIP_COUNT:
            self.sensor_fault = True
            self.sensor_fault_desc = fault_desc
            # sticky: il fault resta finché read_sensor non lo revoca esplicitamente
            self.errors.record(fault_desc, sticky=True, when=now)
            print(f"[DryerController] SENSOR FAULT: {fault_desc}", file=sys.stderr)
            if self.dryer_status:
                print("[DryerController] Emergency stop triggered by sensor fault.", file=sys.stderr)
                self.stop()

        # Return last known good temperature so update_heater stays safe
        last_temp = self.history[-1][1] if self.history else self.set_temp
        return now, last_temp

    # --- heater control (pulse heating) ---
    def update_heater(self, temp):
        if not self.dryer_status:
            self.heater.off()
            self._heat_stall_baseline = None
            self.errors.pop(_HEAT_STALL_KEY, None)
            return

        now = time.monotonic()

        # Cutoff duro, sopra qualunque setpoint: vedi PROCESS_TEMP_HARD_CUTOFF sopra.
        if temp >= PROCESS_TEMP_HARD_CUTOFF:
            self.heater.off()
            self.last_heater_toggle = now
            self._heat_stall_baseline = None
            self.errors.record(_HARD_CUTOFF_KEY, sticky=True)
            print(f"Heater OFF (hard safety cutoff: {temp:.1f}°C >= {PROCESS_TEMP_HARD_CUTOFF:.1f}°C)")
            return
        self.errors.pop(_HARD_CUTOFF_KEY, None)

        needs_heat = temp < (self.set_temp - self.tolerance)
        at_or_above = temp >= self.set_temp

        if self.heater.is_on():
            # turn off immediately if at setpoint or valve open
            if at_or_above:
                self.heater.off()
                self.last_heater_toggle = now
                print(f"Heater OFF (setpoint reached: {temp:.1f}°C >= {self.set_temp:.1f}°C)")
            elif self.valve.is_open():
                self.heater.off()
                self.last_heater_toggle = now
                print("Heater OFF (valve open)")
            elif now - self.last_heater_toggle >= self.heater_on_duration:
                self.heater.off()
                self.last_heater_toggle = now
                print(f"Heater OFF (pulse end, temp: {temp:.1f}°C)")
        else:
            # turn on if below setpoint, pause elapsed, valve closed
            if needs_heat and not self.valve.is_open():
                if now - self.last_heater_toggle >= self.heater_off_duration:
                    self.heater.on()
                    self.last_heater_toggle = now
                    print(f"Heater ON (temp: {temp:.1f}°C, target: {self.set_temp:.1f}°C)")

        if self.heater.is_on():
            if self._heat_stall_baseline is None:
                self._heat_stall_baseline = (now, temp)
            elif now - self._heat_stall_baseline[0] >= _HEAT_STALL_MINUTES * 60:
                _, baseline_temp = self._heat_stall_baseline
                if temp - baseline_temp < _HEAT_STALL_MIN_DELTA:
                    self.errors.record(_HEAT_STALL_KEY, sticky=True)
                else:
                    self.errors.pop(_HEAT_STALL_KEY, None)
                self._heat_stall_baseline = (now, temp)
        else:
            self._heat_stall_baseline = None
            self.errors.pop(_HEAT_STALL_KEY, None)

    # --- logging ---
    def _open_log(self, date: datetime):
        self.log_file = f"logs/temperature_{date.strftime('%Y-%m-%d')}.csv"
        self._log_date = date.date()
        try:
            os.makedirs("logs", exist_ok=True)
        except Exception as e:
            print(f"[DryerController] Cannot create logs directory: {e}")
        if not os.path.exists(self.log_file):
            try:
                with open(self.log_file, "w") as f:
                    f.write("timestamp;temperature;ssr_heater;ssr_fan;setpoint;valve\n")
            except Exception as e:
                print(f"[DryerController] Cannot create log file: {e}")
        files = sorted(glob.glob("logs/temperature_*.csv"))
        for old in files[:-_LOG_MAX_FILES]:
            try:
                os.remove(old)
            except Exception:
                pass

    def log(self, timestamp: datetime, temperature):
        # timestamp is a datetime; rotation depends on its .date()
        if not isinstance(timestamp, datetime):
            timestamp = datetime.now()
        if timestamp.date() != self._log_date:
            self._open_log(timestamp)
        try:
            with open(self.log_file, "a") as f:
                f.write(f"{timestamp.strftime('%Y-%m-%d %H:%M:%S')};{temperature:.2f};{int(self.heater.is_on())};{int(self.fan.is_on())};{self.set_temp:.2f};{int(self.valve.is_open())}\n")
        except Exception as e:
            print(f"[DryerController] Log error: {e}")

    # --- operating hours ---
    _MAX_ELAPSED_HOURS = 24.0  # sanity cap: a single accumulation can't exceed 24h

    def _accumulate_session_hours(self):
        if self.session_start_time is not None:
            elapsed = (time.monotonic() - self.session_start_time) / 3600.0
            elapsed = min(elapsed, self._MAX_ELAPSED_HOURS)
            self.total_hours += elapsed
            self.filter_hours += elapsed
            self.config.set("total_operating_hours", round(self.total_hours, 4))
            self.config.set("filter_operating_hours", round(self.filter_hours, 4))
            self.session_start_time = None

    def get_operating_hours(self):
        partial = 0.0
        if self.dryer_status and self.session_start_time is not None:
            partial = (time.monotonic() - self.session_start_time) / 3600.0
        return {
            "partial_hours": round(partial, 4),
            "total_hours": round(self.total_hours + partial, 4),
            "filter_hours": round(self.filter_hours + partial, 4),
        }

    def periodic_save_hours(self):
        if self.dryer_status and self.session_start_time is not None:
            now = time.monotonic()
            if now - self._hours_save_timer >= 300:
                elapsed = min((now - self.session_start_time) / 3600.0, self._MAX_ELAPSED_HOURS)
                self.config.set("total_operating_hours", round(self.total_hours + elapsed, 4))
                self.config.set("filter_operating_hours", round(self.filter_hours + elapsed, 4))
                self._hours_save_timer = now

    def reset_filter_hours(self):
        self._accumulate_session_hours()
        self.filter_hours = 0.0
        self.config.set("filter_operating_hours", 0.0)
        if self.dryer_status:
            self.session_start_time = time.monotonic()

    def shutdown(self):
        self._accumulate_session_hours()
        try:
            self.heater.off()
            self.fan.off()
            self.valve.cleanup()
            self.fan.cleanup()
            try:
                import RPi.GPIO as GPIO
                GPIO.output(self.heater.gpio_pin, GPIO.LOW)
                GPIO.output(self.fan.gpio_pin, GPIO.LOW)
                GPIO.cleanup()
            except Exception:
                pass
        except Exception as e:
            print(f"[DryerController] Shutdown exception: {e}")

    # --- history / status ---
    def get_history_data(self, mode='1h'):
        now = datetime.now()
        data = list(self.history)
        if not data:
            return []

        if mode == '1m':
            filtered = [x for x in data if (now - x[0]).total_seconds() <= 60]
            return [
                (ts, temp, 1.0 if htr else 0.0, 1.0 if fan else 0.0, vlv)
                for ts, temp, htr, fan, vlv in filtered
            ]

        def _aggregate(filtered, window_start_fn, window_count):
            results = []
            for i in range(window_count):
                ws = window_start_fn(i)
                we = window_start_fn(i + 1) if i + 1 < window_count else now
                window = [x for x in filtered if ws <= x[0] < we]
                if not window:
                    continue
                temps = [x[1] for x in window]
                heaters = [1 if x[2] else 0 for x in window]
                fans = [1 if x[3] else 0 for x in window]
                valves = [1 if x[4] else 0 for x in window]
                n = len(window)
                results.append((
                    ws + (we - ws) / 2,
                    sum(temps) / n,
                    sum(heaters) / n,
                    sum(fans) / n,
                    sum(valves) / n,
                ))
            return results

        if mode == '1h':
            start = now - timedelta(hours=1)
            filtered = [x for x in data if x[0] >= start]
            return _aggregate(filtered, lambda i: start + timedelta(minutes=i), 60)

        if mode == '12h':
            start = now - timedelta(hours=12)
            filtered = [x for x in data if x[0] >= start]
            return _aggregate(filtered, lambda i: start + timedelta(minutes=30 * i), 24)

        raise ValueError("Invalid mode")

    def get_status_data(self):
        if not self.history:
            return datetime.now(), None, False, False, False
        ts, temp, htr, fan, vlv = self.history[-1]
        return ts, temp, htr, fan, vlv

    def apply_config(self):
        """Re-read the tunable parameters from config into the running instance.

        Used instead of rebuilding the controller on a config change: rebuilding
        calls GPIO.cleanup() (leaving the SSRs undefined for a few ms) and drops
        history and the in-progress session while the background thread is still
        holding the old instance.
        """
        self.heater_on_duration = self.config.get("heater_on_duration", 10, int)
        self.heater_off_duration = self.config.get("heater_off_duration", 5, int)
        self.fan_cooldown_duration = self.config.get("fan_cooldown_duration", 120, int)
        self.purge_time = self.config.get("purge_time", 1, int)
        self.cycle_time = self.config.get("cycle_time", 60, int)

        set_temp = self.config.get("setpoint", 70, int)
        self.set_temp = set_temp
        self.tolerance = self.config.get("heater_hysteresis", 1.5, float)

        print("[DryerController] Configuration applied to the running instance.")

    def update_setpoint(self, new_temp):
        self.set_temp = new_temp
        self.config.set("setpoint", new_temp)
        print(f"Setpoint updated to {new_temp}°C")

    def update_fan_cooldown(self):
        if self.cooldown_active and not self.dryer_status and self.fan_cooldown_end:
            if time.monotonic() >= self.fan_cooldown_end:
                self.fan.off()
                self.cooldown_active = False
                print("Fan turned off after cooldown.")

    def update_valve(self):
        if self.dryer_status:
            now = time.monotonic()
            if self.valve.is_open():
                if now - self.valve_last_switch_time >= self.purge_time * 60:
                    self.valve.close()
                    self.valve_last_switch_time = now
            else:
                if now - self.valve_last_switch_time >= self.cycle_time * 60:
                    self.valve.open()
                    self.valve_last_switch_time = now
