# backend/dryer/controller.py
import time
from datetime import datetime, timedelta
from collections import deque
import sys

from backend.dryer.components.heater import Heater
from backend.dryer.components.fan import Fan
from backend.dryer.components.valve import Valve
from backend.dryer.components.sensors import Sensors

class DryerController:
    def __init__(self, config):
        self.config = config

        # heater pulse config
        self.heater_on_duration = self.config.get("heater_on_duration", 10, int)
        self.heater_off_duration = self.config.get("heater_off_duration", 5, int)

        # setpoint
        set_temp = self.config.get("setpoint", 70, int)
        self.set_temp = set_temp
        self.tolerance = set_temp * 0.01

        # fan cooldown
        self.fan_cooldown_duration = self.config.get("fan_cooldown_duration", 120, int)

        # purge / cycle
        self.purge_time = self.config.get("purge_time", 1, int)
        self.cycle_time = self.config.get("cycle_time", 60, int)

        # state
        self.last_heater_toggle = time.time()
        self.history = deque(maxlen=43200)
        self.log_timer = time.time()
        self.dryer_status = False
        self.fan_cooldown_end = None
        self.cooldown_active = False
        self.valve_last_switch_time = time.time()

        # operating hours
        self.total_hours = self.config.get("total_operating_hours", 0.0, float)
        self.filter_hours = self.config.get("filter_operating_hours", 0.0, float)
        self.session_start_time = None
        self._hours_save_timer = time.time()

        self.errors = {}

        # components
        self.heater = Heater()
        self.fan = Fan()
        self.valve = Valve()
        self.sensors = Sensors()

        # log file
        self.log_file = f"logs/temperature_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(self.log_file, "w") as f:
                f.write("timestamp;temperature;ssr_heater;ssr_fan;setpoint;valve\n")
        except Exception as e:
            print(f"[DryerController] Cannot create log file: {e}")

    # --- start / stop ---
    def start(self):
        if not self.dryer_status:
            self.dryer_status = True
            self.cooldown_active = False
            self.fan_cooldown_end = None
            self.session_start_time = time.time()
            self.fan.on()
            self.valve.close()
            self.valve_last_switch_time = time.time()
            self.last_heater_toggle = time.time()
            print("Dryer started.")

    def stop(self):
        if self.dryer_status:
            self._accumulate_session_hours()
            self.dryer_status = False
            self.heater.off()
            print("Dryer stopped.")
            self.fan_cooldown_end = time.time() + self.fan_cooldown_duration
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
    def read_sensor(self):
        try:
            now, temperature = self.sensors.read_all()
            self.errors.clear()
            self.history.append((now, temperature, self.ssr_heater, self.ssr_fan, self.valve_is_open))
            return now, temperature
        except Exception as e:
            print(f"Sensor read error: {e}", file=sys.stderr)
            now = datetime.now()
            if str(e) not in self.errors:
                self.errors[str(e)] = now
            return now, 999

    # --- heater control (pulse heating) ---
    def update_heater(self, temp):
        if not self.dryer_status:
            self.heater.off()
            return

        now = time.time()
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

    # --- logging ---
    def log(self, timestamp, temperature):
        try:
            with open(self.log_file, "a") as f:
                f.write(f"{timestamp};{temperature:.2f};{int(self.heater.is_on())};{int(self.fan.is_on())};{self.set_temp:.2f};{int(self.valve.is_open())}\n")
        except Exception as e:
            print(f"[DryerController] Log error: {e}")

    # --- operating hours ---
    def _accumulate_session_hours(self):
        if self.session_start_time is not None:
            elapsed = (time.time() - self.session_start_time) / 3600.0
            self.total_hours += elapsed
            self.filter_hours += elapsed
            self.config.set("total_operating_hours", round(self.total_hours, 4))
            self.config.set("filter_operating_hours", round(self.filter_hours, 4))
            self.session_start_time = None

    def get_operating_hours(self):
        partial = 0.0
        if self.dryer_status and self.session_start_time is not None:
            partial = (time.time() - self.session_start_time) / 3600.0
        return {
            "partial_hours": round(partial, 4),
            "total_hours": round(self.total_hours + partial, 4),
            "filter_hours": round(self.filter_hours + partial, 4),
        }

    def periodic_save_hours(self):
        if self.dryer_status and self.session_start_time is not None:
            now = time.time()
            if now - self._hours_save_timer >= 300:
                elapsed = (now - self.session_start_time) / 3600.0
                self.config.set("total_operating_hours", round(self.total_hours + elapsed, 4))
                self.config.set("filter_operating_hours", round(self.filter_hours + elapsed, 4))
                self._hours_save_timer = now

    def reset_filter_hours(self):
        self._accumulate_session_hours()
        self.filter_hours = 0.0
        self.config.set("filter_operating_hours", 0.0)
        if self.dryer_status:
            self.session_start_time = time.time()

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
            return datetime.now(), 0.0, False, False, False
        ts, temp, htr, fan, vlv = self.history[-1]
        return ts, temp, htr, fan, vlv

    def update_setpoint(self, new_temp):
        self.set_temp = new_temp
        self.tolerance = new_temp * 0.01
        self.config.set("setpoint", new_temp)
        print(f"Setpoint aggiornato a {new_temp}°C")

    def update_fan_cooldown(self):
        if self.cooldown_active and not self.dryer_status and self.fan_cooldown_end:
            if time.time() >= self.fan_cooldown_end:
                self.fan.off()
                self.cooldown_active = False
                print("Fan turned off after cooldown.")

    def update_valve(self):
        if self.dryer_status:
            now = time.time()
            if self.valve.is_open():
                if now - self.valve_last_switch_time >= self.purge_time * 60:
                    self.valve.close()
                    self.valve_last_switch_time = now
            else:
                if now - self.valve_last_switch_time >= self.cycle_time * 60:
                    self.valve.open()
                    self.valve_last_switch_time = now
