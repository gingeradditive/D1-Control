import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import time

from backend.api.routes import dryer, network, update, config, stats, presets, health, logs
from backend.core.background import background_loop
from backend.core.state import controllers
from backend.core.watchdog import ControlLoopWatchdog, sd_notify

# ---------------------------
# ⚙️ BACKGROUND LOOP (dryer)
# ---------------------------
_running = True
_thread = None
_watchdog = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _thread, _running, _watchdog
    print("[Startup] Avvio ciclo di background del dryer...")
    _thread = Thread(target=background_loop, args=(controllers, lambda: _running))
    _thread.daemon = True
    _thread.start()

    # Deadman sul loop: se si ferma, il riscaldatore va spento comunque.
    _watchdog = ControlLoopWatchdog(controllers, lambda: _running)
    _watchdog.start()

    sd_notify("READY=1")
    yield
    print("[Shutdown] Arresto in corso...")
    sd_notify("STOPPING=1")
    _running = False
    if _thread:
        _thread.join(timeout=3)
    if _watchdog:
        _watchdog.join(timeout=3)
    try:
        controllers["dryer"].shutdown()
    except Exception as e:
        print(f"[Shutdown] Errore in chiusura dryer: {e}")

app = FastAPI(title="Dryer Control API", lifespan=lifespan)

# ---------------------------
# 🔒 CORS CONFIG
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
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
app.include_router(stats.router, prefix="/api/stats", tags=["Stats"])
app.include_router(presets.router, prefix="/api/presets", tags=["Presets"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(logs.router, prefix="/api/logs", tags=["Logs"])

# ---------------------------
# 🚀 ENTRYPOINT (Uvicorn)
# ---------------------------
if __name__ == "__main__":
    # Solo loopback: l'accesso dalla rete passa da nginx (porta 80), che fa da
    # unico punto di ingresso. Gli endpoint distruttivi (update/apply, config/reset,
    # network/connect) non devono essere raggiungibili direttamente dalla LAN.
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)
