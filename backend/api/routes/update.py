import time
from fastapi import APIRouter, HTTPException, BackgroundTasks
from backend.core.state import controllers

router = APIRouter()

@router.get("/version")
def get_version():
    try:
        return controllers["update"].get_current_version()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/check")
def check_updates():
    try:
        return {"updateAvailable": controllers["update"].is_update_available()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def _deferred_reboot():
    """Attende che la risposta HTTP venga inviata, poi riavvia"""
    time.sleep(3)
    controllers["update"].schedule_reboot()

@router.post("/apply")
def apply_update(background_tasks: BackgroundTasks):
    try:
        result = controllers["update"].full_update()
        if result.get("reboot"):
            background_tasks.add_task(_deferred_reboot)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
