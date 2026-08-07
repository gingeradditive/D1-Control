import sys
from pathlib import Path

# Il progetto non installa un pacchetto: aggiunge la root al sys.path cosi'
# `from backend...` funziona indipendentemente da come pytest viene invocato.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
