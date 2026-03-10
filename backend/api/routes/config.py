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

@router.get("/reload")
def reload_config():
    from backend.core.state import controllers

    config = controllers["config"]

    # Properly cleanup the old dryer controller before creating a new one
    old_dryer = controllers.get("dryer")
    if old_dryer:
        old_dryer.shutdown()
    
    controllers["dryer"] = controllers["dryer"].__class__(config)
    controllers["network"] = controllers["network"].__class__()
    controllers["update"] = controllers["update"].__class__(".")
    return {"status": "Success", "message": "Controllers reloaded"}

@router.get("/{key}")
def get(key: str):
    return config.get(key, None)

@router.post("/timezone")
def set_timezone(timezone: str = Form(...)):
    try:
        system.set_timezone(timezone)
        return {"status": "Success", "message": f"Timezone set to {system.get_timezone()}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timezone")
def get_timezone():
    try:
        return {"timezone": system.get_timezone()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/reset")
def factory_reset():
    try:
        config.reset()
        return {"status": "Success", "message": "Configuration reset to factory defaults"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Factory reset failed: {e}")