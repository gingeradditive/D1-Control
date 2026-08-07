import subprocess
import time

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    print("[Network] RPi.GPIO not available, running in simulation mode.")


def connect(ssid: str, password: str) -> bool:
    """Connette il dispositivo a una rete Wi-Fi"""
    if IS_RASPBERRY:
        try:
            result = subprocess.run(
                ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                print(f"[Network] Successfully connected to {ssid}")
                return True
            else:
                print(f"[Network] Connection error: {result.stderr}")
                return False
        except Exception as e:
            print(f"[Network] Exception during connection: {e}")
            return False
    else:
        print(f"[Network] Simulation: connecting to {ssid}")
        time.sleep(2)
        return password == "Success"


def forget() -> bool:
    """Dimentica la connessione Wi-Fi attiva"""
    if IS_RASPBERRY:
        try:
            # Ottieni connessione attiva
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,DEVICE', 'connection', 'show', '--active'],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                print(f"[Network] No active connection: {result.stderr}")
                return False

            for conn in result.stdout.strip().split('\n'):
                if not conn:
                    continue
                name, device = conn.rsplit(":", 1)
                if "wlan" in device:
                    subprocess.run(['nmcli', 'connection', 'delete', name], check=True, timeout=10)
                    print(f"[Network] Connection '{name}' forgotten.")
                    return True
            print("[Network] No Wi-Fi connection found.")
            return False
        except Exception as e:
            print(f"[Network] Error during forget: {e}")
            return False
    else:
        print("[Network] Simulation: connection forgotten.")
        return True
