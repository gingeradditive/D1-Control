from pathlib import Path
from backend.dryer.controller import DryerController
from backend.network.controller import NetworkController
from backend.update.controller import UpdateController
from backend.core.config.file_config import FileConfig
from backend.core.config.system_config import SystemConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

config = FileConfig()

controllers = {
    "config": FileConfig(),
    "dryer": DryerController(config),
    "network": NetworkController(),
    "update": UpdateController(str(PROJECT_ROOT)),
    "system": SystemConfig(),
}
