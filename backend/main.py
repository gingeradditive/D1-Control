import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import time

from backend.api.routes import dryer, network, update, config
from backend.core.background import background_loop
from backend.core.state import controllers

app = FastAPI(title="Dryer Control API")

# ---------------------------
# 🔒 CORS CONFIG
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# 🧩 ROUTER SETUP
# ---------------------------
app.include_router(dryer.router, prefix="/api/dryer", tags=["Dryer"])
app.include_router(network.router, prefix="/api/network", tags=["Network"])
app.include_router(update.router, prefix="/api/update", tags=["Update"])
app.include_router(config.router, prefix="/api/config", tags=["Config"])

# ---------------------------
# ⚙️ BACKGROUND LOOP (dryer)
# ---------------------------
_running = True
_thread = None

@app.on_event("startup")
def startup_event():
    global _thread
    print("[Startup] Avvio ciclo di background del dryer...")
    _thread = Thread(target=background_loop, args=(controllers, lambda: _running))
    _thread.daemon = True
    _thread.start()

@app.on_event("shutdown")
def shutdown_event():
    global _running, _thread
    print("[Shutdown] Arresto in corso...")
    _running = False
    if _thread:
        _thread.join(timeout=3)
    # ferma il dryer e pulisci GPIO
    try:
        controllers["dryer"].shutdown()
    except Exception as e:
        print(f"[Shutdown] Errore in chiusura dryer: {e}")

# ---------------------------
# 🚀 ENTRYPOINT (Uvicorn)
# ---------------------------
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
