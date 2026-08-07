import logging
from pathlib import Path
from backend.update.system_control import run_command

logger = logging.getLogger(__name__)


def mark_directory_safe(project_path: Path):
    run_command(f"git config --global --add safe.directory {project_path}")


def git_pull(project_path: Path) -> str:
    """Esegue git reset --hard e poi git pull per garantire un aggiornamento pulito"""
    mark_directory_safe(project_path)
    run_command("git reset --hard HEAD", cwd=project_path)
    run_command("git clean -fd", cwd=project_path)
    return run_command("git pull", cwd=project_path, env={"LANG": "C", "LC_ALL": "C"})


def get_current_version(project_path: Path) -> dict:
    """Ritorna info sul commit attuale."""
    mark_directory_safe(project_path)
    commit_hash = run_command("git rev-parse HEAD", cwd=project_path)
    commit_msg = run_command("git log -1 --pretty=%B", cwd=project_path)
    commit_date = run_command("git log -1 --date=iso --pretty=format:%cd", cwd=project_path)

    return {
        "commit": commit_hash.strip()[:7],
        "message": commit_msg.strip(),
        "date": commit_date.strip(),
    }


def is_update_available(project_path: Path) -> bool:
    """Controlla se ci sono aggiornamenti disponibili.

    `git fetch` richiede rete: senza connessione non è un errore, è uno stato
    "non determinabile" — trattato come "nessun aggiornamento" invece di far
    fallire la richiesta con un 500 all'apertura della UI.
    """
    try:
        mark_directory_safe(project_path)
        run_command("git fetch", cwd=project_path)
        local = run_command("git rev-parse HEAD", cwd=project_path).strip()
        remote = run_command("git rev-parse @{u}", cwd=project_path).strip()
        return local != remote
    except RuntimeError as e:
        logger.warning(f"Impossibile verificare gli aggiornamenti (probabile assenza di rete): {e}")
        return False
