import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
import time

from backend.api.routes import dryer, network, update, config, stats, presets
from backend.core.background import background_loop
from backend.core.state import controllers

# ---------------------------
# ⚙️ BACKGROUND LOOP (dryer)
# ---------------------------
_running = True
_thread = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _thread, _running
    print("[Startup] Avvio ciclo di background del dryer...")
    _thread = Thread(target=background_loop, args=(controllers, lambda: _running))
    _thread.daemon = True
    _thread.start()
    yield
    print("[Shutdown] Arresto in corso...")
    _running = False
    if _thread:
        _thread.join(timeout=3)
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

# ---------------------------
# 🚀 ENTRYPOINT (Uvicorn)
# ---------------------------
if __name__ == "__main__":
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=False)
