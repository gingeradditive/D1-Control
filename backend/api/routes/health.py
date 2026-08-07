import time
from fastapi import APIRouter
from backend.core.state import controllers, PROCESS_START_TIME

router = APIRouter()


@router.get("/")
def get_health():
    dryer = controllers["dryer"]
    loop_age = dryer.loop_heartbeat_age()
    sensor_age = dryer.sensor_reading_age()
    return {
        "uptime_seconds": time.monotonic() - PROCESS_START_TIME,
        "control_loop": {
            "heartbeat_age_seconds": loop_age,
            "alive": loop_age < 5.0,
        },
        "sensor": {
            "last_reading_age_seconds": None if sensor_age == float("inf") else sensor_age,
            "fault": dryer.sensor_fault,
        },
    }
