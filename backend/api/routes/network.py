from fastapi import APIRouter, HTTPException
from backend.core.state import controllers
from pydantic import BaseModel

class ConnectRequest(BaseModel):
    ssid: str
    password: str

router = APIRouter()

@router.get("/")
def get_networks():
    return controllers["network"].get_networks()

@router.post("/connect")
def connect(request: ConnectRequest):
    if not request.ssid or not request.password:
        raise HTTPException(status_code=400, detail="SSID and password required")
    success = controllers["network"].connect_to_network(request.ssid, request.password)
    return {"status": "success" if success else "error"}

@router.get("/status")
def get_status():
    return controllers["network"].get_connection_status()

@router.get("/g1os")
def check_g1os():
    return {"status": controllers["network"].network_has_g1os()}

@router.post("/forget")
def forget():
    success = controllers["network"].forget_current_connection()
    return {"status": "success" if success else "error"}
