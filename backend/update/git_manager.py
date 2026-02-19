from pathlib import Path
from backend.update.system_control import run_command


def mark_directory_safe(project_path: Path):
    run_command(f"git config --global --add safe.directory {project_path}")


def git_pull(project_path: Path) -> str:
    """Esegue git reset --hard e poi git pull per garantire un aggiornamento pulito"""
    mark_directory_safe(project_path)
    run_command("git reset --hard HEAD", cwd=project_path)
    run_command("git clean -fd", cwd=project_path)
    return run_command("git pull", cwd=project_path)


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
    """Controlla se ci sono aggiornamenti disponibili"""
    mark_directory_safe(project_path)
    run_command("git fetch", cwd=project_path)
    local = run_command("git rev-parse HEAD", cwd=project_path).strip()
    remote = run_command("git rev-parse @{u}", cwd=project_path).strip()
    return local != remote
