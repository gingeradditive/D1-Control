import logging
from pathlib import Path
from backend.update.git_manager import git_pull, get_current_version, is_update_available
from backend.update.dependencies import install_backend_dependencies
from backend.update.frontend_builder import build_frontend
from backend.update.system_control import reboot_device

logger = logging.getLogger(__name__)


class UpdateController:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()

    def full_update(self) -> dict:
        """Esegue git pull, aggiorna backend, builda frontend e programma il riavvio.
        Returns a dict with status info so the caller can respond before reboot."""
        steps_completed = []

        try:
            logger.info("Eseguo git pull...")
            output = git_pull(self.project_path)
            steps_completed.append("git_pull")

            if "Already up to date." in output or "Già aggiornato" in output:
                logger.info("Nessun aggiornamento trovato.")
                return {"updateApplied": False, "message": "Already up to date.", "steps": steps_completed}

            logger.info("Aggiorno dipendenze backend...")
            install_backend_dependencies(self.project_path)
            steps_completed.append("backend_deps")

            logger.info("Ricostruisco il frontend...")
            build_frontend(self.project_path)
            steps_completed.append("frontend_build")

        except Exception as e:
            logger.error(f"Update failed at steps {steps_completed}: {e}")
            return {"updateApplied": False, "message": f"Update failed: {e}", "steps": steps_completed, "error": True}

        return {"updateApplied": True, "message": "Update applied. Rebooting...", "steps": steps_completed, "reboot": True}

    def schedule_reboot(self):
        """Riavvia il dispositivo — da chiamare dopo aver inviato la risposta HTTP"""
        logger.info("Riavvio programmato in corso...")
        reboot_device()

    def get_current_version(self) -> dict:
        return get_current_version(self.project_path)

    def is_update_available(self) -> bool:
        return is_update_available(self.project_path)
