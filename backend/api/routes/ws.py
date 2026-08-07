import asyncio
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.core.state import controllers

router = APIRouter()

_PUSH_INTERVAL_SECONDS = 1.0


def _status_payload():
    dryer = controllers["dryer"]
    ts, temp, heater, fan, valve = dryer.get_status_data()
    elapsed = 0
    if dryer.dryer_status and dryer.session_start_time is not None:
        elapsed = int(time.monotonic() - dryer.session_start_time)
    current_temp = None if dryer.sensor_fault or temp is None else round(temp, 2)
    return {
        "setpoint": dryer.set_temp,
        "current_temp": current_temp,
        "heater": heater,
        "fan": fan,
        "status": dryer.dryer_status,
        "valve": valve,
        "errors": dryer.errors.snapshot(),
        "sensor_fault": dryer.sensor_fault,
        "drying_elapsed_seconds": elapsed,
    }


@router.websocket("/status")
async def ws_status(websocket: WebSocket):
    """Sostituisce il polling HTTP di /api/dryer/status (86400 richieste/giorno
    a 1 req/s) con un'unica connessione persistente: il backend spinge lo stato
    ogni secondo, solo se è cambiato rispetto all'ultimo invio."""
    await websocket.accept()
    last_sent = None
    try:
        while True:
            payload = _status_payload()
            if payload != last_sent:
                await websocket.send_json(payload)
                last_sent = payload
            await asyncio.sleep(_PUSH_INTERVAL_SECONDS)
    except WebSocketDisconnect:
        pass
