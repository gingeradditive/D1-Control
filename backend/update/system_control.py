import getpass
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    logger.warning("RPi.GPIO not available, running in simulation mode.")

# Il servizio dryer-backend gira con MemoryMax=400M: `npm install` e `npm run build`
# lanciati come processi figli restano nello stesso cgroup e vengono uccisi dall'OOM
# killer. Questo prefisso li sposta in uno scope transiente senza limiti di memoria,
# tornando comunque all'utente non privilegiato tramite runuser.
# NOTA: deve restare identico alla regola in scripts/install.sh (sudoers).
UPDATE_SCOPE_UNIT = "dryer-update"


def _scope_prefix(user: str) -> list:
    return [
        "sudo", "-n", "systemd-run", "--scope", "--quiet", "--collect",
        f"--unit={UPDATE_SCOPE_UNIT}",
        "-p", "MemoryMax=infinity", "-p", "MemorySwapMax=infinity",
        "runuser", "-u", user, "--", "/bin/sh", "-c",
    ]


_scope_available = None


def _can_escape_cgroup(user: str) -> bool:
    """Verifica una sola volta che sudo+systemd-run siano utilizzabili senza password"""
    global _scope_available
    if _scope_available is None:
        if shutil.which("systemd-run") is None or shutil.which("runuser") is None:
            _scope_available = False
        else:
            probe = subprocess.run(
                _scope_prefix(user) + ["true"],
                capture_output=True, text=True, timeout=30,
            )
            _scope_available = probe.returncode == 0
            if not _scope_available:
                logger.warning(
                    "systemd-run not usable (%s): the update will run in the "
                    "service's cgroup and may be killed by the OOM killer",
                    probe.stderr.strip() or f"rc={probe.returncode}",
                )
    return _scope_available


def run_command(command: str, cwd: Path = None, timeout: int = 300, env: dict = None,
                unrestricted: bool = False) -> str:
    """Esegue un comando shell e ritorna l'output o solleva un'eccezione.

    Con `unrestricted=True` il comando viene eseguito in uno scope systemd separato,
    fuori dai limiti di memoria del servizio backend.
    """
    import os
    merged_env = {**os.environ, **(env or {})}
    user = getpass.getuser()
    if unrestricted and _can_escape_cgroup(user):
        argv = _scope_prefix(user) + [command]
        use_shell = False
    else:
        argv = command
        use_shell = True
    try:
        logger.debug(f"Running: {command} (cwd={cwd}, unrestricted={unrestricted})")
        result = subprocess.run(
            argv,
            shell=use_shell,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=merged_env,
        )
        if result.returncode != 0:
            logger.error(f"Command failed (rc={result.returncode}): {result.stderr.strip()}")
            raise RuntimeError(result.stderr.strip())
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"Command '{command}' timed out after {timeout}s")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Command '{command}' failed: {e}")


def reboot_device():
    """Riavvia il Raspberry (o salta in ambiente non-RPi)"""
    if IS_RASPBERRY:
        logger.info("Rebooting the Raspberry Pi...")
        run_command("sudo reboot")
    else:
        logger.info("[DEBUG] Reboot skipped (non-Raspberry environment)")
