import time
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import JSONResponse
from backend.core.state import controllers

router = APIRouter()

@router.get("/status")
def get_status():
    dryer = controllers["dryer"]
    ts, temp, heater, fan, valve = dryer.get_status_data()
    elapsed = 0
    if dryer.dryer_status and dryer.session_start_time is not None:
        elapsed = int(time.monotonic() - dryer.session_start_time)
    # Con un fault sensore il valore in memoria è l'ultima lettura buona, tenuta
    # solo per far lavorare update_heater in sicurezza. Esporla mostrerebbe un
    # numero fermo che sembra valido: meglio nessun valore, la UI mostra "--".
    current_temp = None if dryer.sensor_fault or temp is None else round(temp)
    return {
        "setpoint": dryer.set_temp,
        "current_temp": current_temp,
        "heater": heater,
        "fan": fan,
        "status": dryer.dryer_status,
        "valve": valve,
        "errors": dryer.errors,
        "sensor_fault": dryer.sensor_fault,
        "drying_elapsed_seconds": elapsed,
    }

@router.post("/status/{status}")
def set_status(status: bool):
    dryer = controllers["dryer"]
    if status:
        # start() è l'unica fonte di verità: può rifiutare l'avvio anche se il
        # fault è comparso tra la richiesta e questo istante.
        if not dryer.start():
            fault_detail = dryer.errors.get("sensor_fault", "Sensor fault detected")
            return JSONResponse(
                status_code=409,
                content={
                    "error": "sensor_fault",
                    "detail": fault_detail,
                    "status": "running" if dryer.dryer_status else "stopped",
                    "running": dryer.dryer_status,
                },
            )
    else:
        dryer.stop()
    return {
        "status": "running" if dryer.dryer_status else "stopped",
        "running": dryer.dryer_status,
    }

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
    if not (0 <= value <= 90):
        raise HTTPException(status_code=422, detail="Setpoint out of range [0, 90]°C")
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
    if hours < 0 or hours > 100000:
        raise HTTPException(status_code=422, detail="Filter hours out of range [0, 100000]")
    dryer = controllers["dryer"]
    dryer._accumulate_session_hours()
    dryer.filter_hours = hours
    dryer.config.set("filter_operating_hours", round(hours, 4))
    if dryer.dryer_status:
        dryer.session_start_time = __import__("time").monotonic()
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
