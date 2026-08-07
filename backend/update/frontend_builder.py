from pathlib import Path
from backend.update.system_control import run_command


def build_frontend(project_path: Path):
    """Installa le dipendenze e ricostruisce il frontend"""
    frontend_path = project_path / "frontend"
    # unrestricted: la build Vite/Rollup non sta nel MemoryMax del servizio backend
    run_command("npm install", cwd=frontend_path, timeout=900, unrestricted=True)
    run_command("npm run build", cwd=frontend_path, timeout=900, unrestricted=True)
