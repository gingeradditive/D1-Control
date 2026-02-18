import time
from datetime import datetime

def background_loop(controllers, is_running):
    dryer = controllers["dryer"]

    while is_running():
        dryer.update_fan_cooldown()
        dryer.update_valve()
        now, max6675_temp, hum_abs, sht40_temp, dew_point = dryer.read_sensor()
        dryer.update_heater_pid_discrete(max6675_temp)

        dryer.periodic_save_hours()

        if time.time() - dryer.log_timer >= 10:
            dryer.log_timer = time.time()
            dryer.log(now.strftime('%Y-%m-%d %H:%M:%S'),
                      max6675_temp, dew_point, sht40_temp)
        time.sleep(1)
