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
    """
    Façade compatibile con l'API originale.
    Internamente usa componenti separati per heater/fan/valve/sensors.
    """
    def __init__(self, config):
        # config
        self.config = config
        self.last_heater_action = time.time()
        self.heater_pulse_duration = self.config.get("heater_pulse_duration", 10, int)
        self.Kp = self.config.get("heater_kp", 5.0, float)
        self.Ki = self.config.get("heater_ki", 0.1, float)
        self.min_pause = self.config.get("heater_min_pause", 5, int)
        self.max_pause = self.config.get("heater_max_pause", 60, int)
        set_temp = self.config.get("setpoint", 70, int)
        self.fan_cooldown_duration = self.config.get("fan_cooldown_duration", 120, int)
        self.valve_open_interval = self.config.get("valve_open_interval", 15, int)
        self.valve_close_interval = self.config.get("valve_close_interval", 5, int)

        # system vars
        self.integral_error = 0.0
        self.set_temp = set_temp
        self.tolerance = set_temp * 0.01
        self.history = deque(maxlen=43200)
        self.log_timer = time.time()
        self.dryer_status = False
        self.fan_cooldown_end = None
        self.cooldown_active = False
        self.valve_last_switch_time = time.time()
        self.hum_abs = 0.0

        self.errors = {}

        # components
        self.heater = Heater()
        self.fan = Fan()
        self.valve = Valve()
        self.sensors = Sensors()

        # setup log file (same pattern as original)
        self.log_file = f"logs/temperature_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(self.log_file, "w") as f:
                f.write("timestamp;max6675_temp;sht40_temp;dew_point;ssr_heater;ssr_fan;setpoint;valve\n")
        except Exception as e:
            print(f"[DryerController] Cannot create log file: {e}")

    # --- compatibility methods (start/stop) ---
    def start(self):
        if not self.dryer_status:
            self.dryer_status = True
            self.cooldown_active = False
            self.fan_cooldown_end = None
            self.fan.on()
            self.valve.close()
            self.valve_last_switch_time = time.time()
            print("Heater started.")
    
    def stop(self):
        if self.dryer_status:
            self.dryer_status = False
            self.heater.off()
            print("Heater stopped.")
            self.fan_cooldown_end = time.time() + self.fan_cooldown_duration
            self.cooldown_active = True
            self.valve.close()
            print("Fan cooldown started.")

    # wrapper helpers to expose same attributes used externally in existing code
    @property
    def ssr_heater(self):
        return self.heater.is_on()

    @ssr_heater.setter
    def ssr_heater(self, v: bool):
        # not used normally but kept for API parity
        if v:
            self.heater.on()
        else:
            self.heater.off()

    @property
    def ssr_fan(self):
        return self.fan.is_on()

    @ssr_fan.setter
    def ssr_fan(self, v: bool):
        if v:
            self.fan.on()
        else:
            self.fan.off()

    @property
    def valve_is_open(self):
        return self.valve.is_open()

    @valve_is_open.setter
    def valve_is_open(self, v: bool):
        if v:
            self.valve.open()
        else:
            self.valve.close()

    # --- sensor read (compatibile) ---
    def read_sensor(self):
        try:
            now, max6675_temp, ah, sht_temp, dew_point = self.sensors.read_all()
            # clear errors if successful
            self.errors.clear()
            # append to history (preserve original tuple layout)
            self.history.append((now, max6675_temp, sht_temp, dew_point, self.ssr_heater, self.ssr_fan, self.valve_is_open))
            self.hum_abs = ah
            return now, max6675_temp, ah, sht_temp, dew_point
        except Exception as e:
            # keep behavior: log error and return sentinel values
            print(f"Errore lettura sensori: {e}", file=sys.stderr)
            now = datetime.now()
            if str(e) not in self.errors:
                self.errors[str(e)] = now
            return now, 999, 999, 999, 999

    # --- PID discrete (compatibile) ---
    def update_heater_pid_discrete(self, temp):
        if not self.dryer_status:
            self.heater.off()
            return

        now = time.time()
        error = self.set_temp - temp
        self.integral_error += error * 1.0

        raw_pause = self.max_pause - (self.Kp * error + self.Ki * self.integral_error)
        pause_duration = max(self.min_pause, min(self.max_pause, raw_pause))

        if error > self.tolerance and not self.heater.is_on() and not self.valve.is_open():
            if now - self.last_heater_action >= pause_duration:
                self.heater.on()
                self.last_heater_action = now
                print(f"[+{error:.2f}°C] Heater ON per {self.heater_pulse_duration}s (pause: {pause_duration:.1f}s)")
        elif self.valve.is_open() and self.heater.is_on():
            self.heater.off()
            self.last_heater_action = now
            print("Heater OFF (valve opened)")
        elif self.heater.is_on() and now - self.last_heater_action >= self.heater_pulse_duration:
            self.heater.off()
            self.last_heater_action = now
            print("Heater OFF")

    # --- logging ---
    def log(self, timestamp, max6675_temp, dew_point, sht40_temp):
        try:
            with open(self.log_file, "a") as f:
                f.write(f"{timestamp};{max6675_temp:.2f};{sht40_temp:.2f};{dew_point:.2f};{int(self.heater.is_on())};{int(self.fan.is_on())};{self.set_temp:.2f};{int(self.valve.is_open())}\n")
        except Exception as e:
            print(f"[DryerController] Log error: {e}")

    def shutdown(self):
        # make sure all actuators are turned off and resources cleaned
        try:
            self.heater.off()
            self.fan.off()
            self.valve.cleanup()
            # If running on Raspberry, also cleanup GPIO to be safe
            try:
                import RPi.GPIO as GPIO
                GPIO.output(self.heater.gpio_pin, GPIO.LOW)
                GPIO.output(self.fan.gpio_pin, GPIO.LOW)
                GPIO.cleanup()
            except Exception:
                pass
        except Exception as e:
            print(f"[DryerController] Shutdown exception: {e}")

    # --- history/status (compatibile with existing API) ---
    def get_history_data(self, mode='1h'):
        # reuse old code but reading from self.history (already same shape)
        now = datetime.now()
        data = list(self.history)
        if not data:
            return []

        if mode == '1m':
            filtered = [x for x in data if (now - x[0]).total_seconds() <= 60]
            results = []
            for timestamp, max6675_temp, sht40_temp, dew_point, ssr_heater, ssr_fan, valve in filtered:
                heater_ratio = 1.0 if ssr_heater else 0.0
                fan_ratio = 1.0 if ssr_fan else 0.0
                results.append((timestamp, max6675_temp, dew_point, heater_ratio, fan_ratio, max6675_temp, max6675_temp, dew_point, dew_point, valve))
            return results

        if mode == '1h':
            start = now - timedelta(hours=1)
            filtered = [x for x in data if x[0] >= start]
            results = []
            for i in range(60):
                window_start = start + timedelta(minutes=i)
                window_end = window_start + timedelta(minutes=1)
                window_data = [x for x in filtered if window_start <= x[0] < window_end]
                if not window_data:
                    continue
                temps = [x[1] for x in window_data]
                dews = [x[3] for x in window_data]
                heaters = [1 if x[4] else 0 for x in window_data]
                fans = [1 if x[5] else 0 for x in window_data]
                timestamp = window_start + timedelta(seconds=30)
                valve = [1 if x[6] else 0 for x in window_data]
                temp_avg = sum(temps) / len(temps)
                dews_avg = sum(dews) / len(dews)
                heater_ratio = sum(heaters) / len(heaters)
                fan_ratio = sum(fans) / len(fans)
                valve_ration = sum(valve) / len(valve)
                results.append((timestamp, temp_avg, dews_avg, heater_ratio, fan_ratio, min(temps), max(temps), min(dews), max(dews), valve_ration))
            return results

        if mode == '12h':
            start = now - timedelta(hours=12)
            filtered = [x for x in data if x[0] >= start]
            results = []
            for i in range(24):
                window_start = start + timedelta(minutes=30*i)
                window_end = window_start + timedelta(minutes=30)
                window_data = [x for x in filtered if window_start <= x[0] < window_end]
                if not window_data:
                    continue
                temps = [x[1] for x in window_data]
                dews = [x[3] for x in window_data]
                heaters = [1 if x[4] else 0 for x in window_data]
                fans = [1 if x[5] else 0 for x in window_data]
                timestamp = window_start + timedelta(minutes=15)
                valve = [1 if x[6] else 0 for x in window_data]
                temp_avg = sum(temps) / len(temps)
                dews_avg = sum(dews) / len(dews)
                heater_ratio = sum(heaters) / len(heaters)
                fan_ratio = sum(fans) / len(fans)
                valve_ration = sum(valve) / len(valve)
                results.append((timestamp, temp_avg, dews_avg, heater_ratio, fan_ratio, min(temps), max(temps), min(dews), max(dews), valve_ration))
            return results

        raise ValueError("Invalid mode")

    def get_status_data(self):
        if not self.history:
            data = datetime.now(), 0.0, 0.0, 0.0, 0.0, 0.0, False, False
            return data
        (timestamp, max6675_temp, sht40_temp, dew_point, ssr_heater, ssr_fan, valve) = self.history[-1]
        return (timestamp, max6675_temp, sht40_temp, dew_point, ssr_heater, ssr_fan, self.dryer_status, valve, self.hum_abs)

    def aggregate_data(self, data, now, interval_seconds, window_seconds):
        buckets = {}
        for (t, temp, hum, status) in data:
            delta = (now - t).total_seconds()
            if delta <= window_seconds:
                bucket_key = int(delta // interval_seconds)
                buckets.setdefault(bucket_key, []).append((temp, hum, status))

        result = []
        for key in sorted(buckets.keys()):
            bucket = buckets[key]
            if bucket:
                avg_temp = sum(t for t, _, _ in bucket) / len(bucket)
                avg_hum = sum(h for _, h, _ in bucket) / len(bucket)
                heater_ratio = sum(1 for _, _, s in bucket if s) / len(bucket)
                bucket_time = now - timedelta(seconds=key * interval_seconds)
                result.append((bucket_time, avg_temp, avg_hum, heater_ratio))
        return result

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

    def valve_open(self):
        self.valve.open()

    def valve_close(self):
        self.valve.close()

    def update_valve(self):
        if self.dryer_status:
            now = time.time()
            if self.valve.is_open():
                if now - self.valve_last_switch_time >= self.valve_open_interval * 60:
                    self.valve.close()
                    self.valve_last_switch_time = now
            else:
                if now - self.valve_last_switch_time >= self.valve_close_interval * 60:
                    self.valve.open()
                    self.valve_last_switch_time = now
