import httpx
from fastapi import FastAPI, Request
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

    async with httpx.AsyncClient(follow_redirects=True) as client:
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

    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.request(
            method, url, content=body, headers=headers
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp.headers
    )
