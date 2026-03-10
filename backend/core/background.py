import time

def background_loop(controllers, is_running):
    while is_running():
        dryer = controllers["dryer"]
        dryer.update_fan_cooldown()
        dryer.update_valve()
        now, temperature = dryer.read_sensor()
        dryer.update_heater(temperature)
        dryer.periodic_save_hours()

        if time.time() - dryer.log_timer >= 10:
            dryer.log_timer = time.time()
            dryer.log(now.strftime('%Y-%m-%d %H:%M:%S'), temperature)
        time.sleep(1)
