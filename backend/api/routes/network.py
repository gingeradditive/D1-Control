from fastapi import APIRouter, HTTPException
from backend.core.state import controllers

router = APIRouter()
network = controllers["network"]

@router.get("/")
def get_networks():
    return network.get_networks()

@router.post("/{ssid}/password")
def connect(ssid: str, request: dict):
    password = request.get("password")
    if not ssid or not password:
        raise HTTPException(status_code=400, detail="SSID and password required")
    success = network.connect_to_network(ssid, password)
    return {"status": "success" if success else "error"}

@router.get("/status")
def get_status():
    return network.get_connection_status()

@router.get("/g1os")
def check_g1os():
    return {"status": network.network_has_g1os()}

@router.post("/forget")
def forget():
    success = network.forget_current_connection()
    return {"status": "success" if success else "error"}
