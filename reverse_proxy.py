import asyncio
import httpx
import websockets
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND = "http://localhost:5173"
BACKEND = "http://localhost:8000"
BACKEND_WS = "ws://localhost:8000"

# ===================== WEBSOCKET =====================
@app.websocket("/ws/{path:path}")
async def proxy_ws(websocket: WebSocket, path: str):
    await websocket.accept()
    url = f"{BACKEND_WS}/ws/{path}"
    try:
        async with websockets.connect(url) as backend_ws:
            async def client_to_backend():
                try:
                    while True:
                        data = await websocket.receive_text()
                        await backend_ws.send(data)
                except WebSocketDisconnect:
                    pass

            async def backend_to_client():
                async for message in backend_ws:
                    await websocket.send_text(message)

            client_task = asyncio.ensure_future(client_to_backend())
            backend_task = asyncio.ensure_future(backend_to_client())
            done, pending = await asyncio.wait(
                [client_task, backend_task], return_when=asyncio.FIRST_COMPLETED
            )
            for task in pending:
                task.cancel()
    except Exception:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass

# ===================== API =====================
@app.api_route("/api/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_api(request: Request, path: str):
    url = f"{BACKEND}/api/{path}"
    method = request.method

    body = await request.body()

    # Rimuove header problematici
    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["host", "content-length"]
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        resp = await client.request(
            method, url, content=body, headers=headers
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp.headers
    )

# ===================== FRONTEND =====================
@app.api_route("/{path:path}", methods=["GET","POST","PUT","PATCH","DELETE"])
async def proxy_frontend(request: Request, path: str):
    url = f"{FRONTEND}/{path}"
    method = request.method

    body = await request.body()

    headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in ["host", "content-length"]
    }

    async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
        resp = await client.request(
            method, url, content=body, headers=headers
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp.headers
    )
