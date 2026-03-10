import time
from fastapi import APIRouter, Query
from backend.core.state import controllers

router = APIRouter()

@router.get("/status")
def get_status():
    dryer = controllers["dryer"]
    ts, temp, heater, fan, valve = dryer.get_status_data()
    elapsed = 0
    if dryer.dryer_status and dryer.session_start_time is not None:
        elapsed = int(time.time() - dryer.session_start_time)
    return {
        "setpoint": dryer.set_temp,
        "current_temp": round(temp),
        "heater": heater,
        "fan": fan,
        "status": dryer.dryer_status,
        "valve": valve,
        "errors": dryer.errors,
        "drying_elapsed_seconds": elapsed,
    }

@router.post("/status/{status}")
def set_status(status: bool):
    dryer = controllers["dryer"]
    dryer.start() if status else dryer.stop()
    return {"status": "running" if status else "stopped"}

@router.get("/history")
def get_history(mode: str = Query(default="1h", enum=["1m", "1h", "12h"])):
    dryer = controllers["dryer"]
    history = dryer.get_history_data(mode)
    return {
        "mode": mode,
        "history": [
            {
                "timestamp": t.strftime("%Y-%m-%d %H:%M:%S"),
                "temperature": round(temp, 2),
                "heater_ratio": round(hr, 2),
                "fan_ratio": round(fr, 2),
                "valve": round(valve, 2),
            }
            for t, temp, hr, fr, valve in history
        ]
    }

@router.post("/setpoint/{value}")
def set_setpoint(value: float):
    dryer = controllers["dryer"]
    dryer.update_setpoint(value)
    return {"setpoint": dryer.set_temp}

@router.post("/filter/reset")
def reset_filter_hours():
    dryer = controllers["dryer"]
    dryer.reset_filter_hours()
    return {"filter_hours": 0.0}

@router.post("/filter/set/{hours}")
def set_filter_hours(hours: float):
    dryer = controllers["dryer"]
    dryer._accumulate_session_hours()
    dryer.filter_hours = hours
    dryer.config.set("filter_operating_hours", round(hours, 4))
    if dryer.dryer_status:
        dryer.session_start_time = __import__("time").time()
    return {"filter_hours": hours}

@router.get("/purge-time")
def get_purge_time():
    dryer = controllers["dryer"]
    return {"purge_time": dryer.purge_time}

@router.post("/purge-time/{seconds}")
def set_purge_time(seconds: int):
    dryer = controllers["dryer"]
    dryer.purge_time = seconds
    dryer.config.set("purge_time", seconds)
    return {"purge_time": seconds}

@router.get("/cycle-time")
def get_cycle_time():
    dryer = controllers["dryer"]
    return {"cycle_time": dryer.cycle_time}

@router.post("/cycle-time/{seconds}")
def set_cycle_time(seconds: int):
    dryer = controllers["dryer"]
    dryer.cycle_time = seconds
    dryer.config.set("cycle_time", seconds)
    return {"cycle_time": seconds}
