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
            print(f"[SystemConfig] Error listing timezones: {e}")
            return []

    def set_timezone(self, timezone: str) -> bool:
        """Imposta la timezone di sistema.

        Solleva RuntimeError se il comando fallisce: il chiamante deve
        propagare l'errore, non dichiarare successo.
        """
        known = self.list_timezones()
        if known and timezone not in known:
            raise RuntimeError(f"Invalid timezone: {timezone}")
        try:
            subprocess.run(
                ["sudo", "-n", "timedatectl", "set-timezone", timezone],
                capture_output=True, text=True, check=True, timeout=15
            )
        except subprocess.CalledProcessError as e:
            detail = (e.stderr or "").strip() or f"exit code {e.returncode}"
            print(f"[SystemConfig] Error setting timezone: {detail}")
            raise RuntimeError(f"timedatectl set-timezone failed: {detail}") from e
        except Exception as e:
            print(f"[SystemConfig] Unknown error: {e}")
            raise RuntimeError(f"Unable to set timezone: {e}") from e

        applied = self.get_timezone()
        if applied != timezone:
            raise RuntimeError(
                f"Timezone not applied: requested {timezone}, current {applied}"
            )
        print(f"[SystemConfig] Timezone set to: {timezone}")
        return True

    def get_timezone(self) -> str:
        try:
            result = subprocess.run(
                ["timedatectl", "show", "-p", "Timezone", "--value"],
                capture_output=True, text=True, check=True, timeout=10
            )
            return result.stdout.strip()
        except Exception as e:
            print(f"[SystemConfig] Error retrieving timezone: {e}")
            return "Unknown"
