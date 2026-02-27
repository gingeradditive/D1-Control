import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    logger.warning("RPi.GPIO not available, running in simulation mode.")


def run_command(command: str, cwd: Path = None, timeout: int = 300) -> str:
    """Esegue un comando shell e ritorna l'output o solleva un'eccezione"""
    try:
        logger.debug(f"Running: {command} (cwd={cwd})")
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout
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
        logger.info("Riavvio del Raspberry Pi...")
        run_command("sudo reboot")
    else:
        logger.info("[DEBUG] Reboot skipped (non-Raspberry environment)")
