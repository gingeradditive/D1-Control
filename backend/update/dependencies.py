import shlex
from pathlib import Path
from backend.update.system_control import run_command


def install_backend_dependencies(project_path: Path):
    """Installa i pacchetti Python richiesti dal backend"""
    venv_pip = project_path / "venv" / "bin" / "pip"
    run_command(f"{shlex.quote(str(venv_pip))} install -r requirements.txt", cwd=project_path,
                timeout=900, unrestricted=True)
