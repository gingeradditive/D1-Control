import time
from pathlib import Path
from backend.dryer.controller import DryerController
from backend.network.controller import NetworkController
from backend.update.controller import UpdateController
from backend.core.config.file_config import FileConfig
from backend.core.config.system_config import SystemConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# monotonic: sopravvive a un cambio di orario di sistema, usato per l'uptime in /api/health
PROCESS_START_TIME = time.monotonic()

config = FileConfig()

controllers = {
    "config": config,
    "dryer": DryerController(config),
    "network": NetworkController(),
    "update": UpdateController(str(PROJECT_ROOT)),
    "system": SystemConfig(),
}
