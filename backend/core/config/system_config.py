import subprocess

class SystemConfig:
    """Gestione impostazioni di sistema come timezone"""

    def list_timezones(self) -> list[str]:
        try:
            result = subprocess.run(
                ["timedatectl", "list-timezones"],
                capture_output=True, text=True, check=True, timeout=10
            )
            return [tz for tz in result.stdout.split() if tz]
        except Exception as e:
            print(f"[SystemConfig] Errore nell'elenco timezone: {e}")
            return []

    def set_timezone(self, timezone: str) -> bool:
        """Imposta la timezone di sistema.

        Solleva RuntimeError se il comando fallisce: il chiamante deve
        propagare l'errore, non dichiarare successo.
        """
        known = self.list_timezones()
        if known and timezone not in known:
            raise RuntimeError(f"Timezone non valida: {timezone}")
        try:
            subprocess.run(
                ["sudo", "-n", "timedatectl", "set-timezone", timezone],
                capture_output=True, text=True, check=True, timeout=15
            )
        except subprocess.CalledProcessError as e:
            detail = (e.stderr or "").strip() or f"exit code {e.returncode}"
            print(f"[SystemConfig] Errore nell'impostare timezone: {detail}")
            raise RuntimeError(f"timedatectl set-timezone fallito: {detail}") from e
        except Exception as e:
            print(f"[SystemConfig] Errore sconosciuto: {e}")
            raise RuntimeError(f"Impossibile impostare la timezone: {e}") from e

        applied = self.get_timezone()
        if applied != timezone:
            raise RuntimeError(
                f"Timezone non applicata: richiesta {timezone}, attuale {applied}"
            )
        print(f"[SystemConfig] Timezone impostato su: {timezone}")
        return True

    def get_timezone(self) -> str:
        try:
            result = subprocess.run(
                ["timedatectl", "show", "-p", "Timezone", "--value"],
                capture_output=True, text=True, check=True, timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            print(f"[SystemConfig] Errore nel recupero timezone: {e}")
            return "Sconosciuto"
