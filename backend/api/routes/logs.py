import subprocess
from fastapi import APIRouter, HTTPException, Query

router = APIRouter()

SERVICE_UNIT = "dryer-backend.service"
MAX_LINES = 1000


@router.get("/")
def get_logs(lines: int = Query(default=200, ge=1, le=MAX_LINES)):
    """Ultime righe di log del servizio, lette da journald.

    Richiede che l'utente del servizio sia nel gruppo systemd-journal
    (vedi scripts/install.sh) — nessun sudo necessario.
    """
    try:
        result = subprocess.run(
            ["journalctl", "-u", SERVICE_UNIT, "-n", str(lines), "--no-pager", "-o", "short-iso"],
            capture_output=True, text=True, timeout=10,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=501, detail="journalctl not available on this system")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="journalctl did not respond in time")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr.strip() or "journalctl failed")

    return {"lines": result.stdout.splitlines()}
