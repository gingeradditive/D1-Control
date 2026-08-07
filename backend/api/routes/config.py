from fastapi import APIRouter, Form, HTTPException
from backend.core.state import controllers

router = APIRouter()
config = controllers["config"]
system = controllers["system"]

@router.get("/")
def get_all_config():
    return config.all()

@router.post("/set")
def set_config(key: str = Form(...), value: str = Form(...)):
    config.set(key, value)
    return {"status": "Success", "message": "Configuration updated"}

@router.post("/apply")
def apply_config():
    """Push the saved configuration into the running controller.

    Preferred over /reload: no GPIO cleanup, no lost history, no lost session.
    """
    dryer = controllers.get("dryer")
    if dryer is None:
        raise HTTPException(status_code=503, detail="Dryer controller not available")
    try:
        dryer.apply_config()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to apply configuration: {e}")
    return {"status": "Success", "message": "Configuration applied"}

@router.post("/reload")
def reload_config():
    from backend.core.state import controllers, PROJECT_ROOT

    cfg = controllers["config"]

    old_dryer = controllers.get("dryer")
    if old_dryer:
        old_dryer.shutdown()

    controllers["dryer"] = controllers["dryer"].__class__(cfg)
    controllers["network"] = controllers["network"].__class__()
    controllers["update"] = controllers["update"].__class__(str(PROJECT_ROOT))
    return {"status": "Success", "message": "Controllers reloaded"}

@router.get("/timezone")
def get_timezone():
    try:
        return {"timezone": system.get_timezone()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/timezone")
def set_timezone(timezone: str = Form(...)):
    try:
        system.set_timezone(timezone)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "Success", "message": f"Timezone set to {system.get_timezone()}"}

@router.post("/reset")
def factory_reset():
    try:
        config.reset()
        return {"status": "Success", "message": "Configuration reset to factory defaults"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Factory reset failed: {e}")

@router.get("/{key}")
def get(key: str):
    return config.all().get(key)