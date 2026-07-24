import subprocess
import socket

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    print("[Network] RPi.GPIO not available, running in simulation mode.")


def get_status() -> dict:
    """Restituisce lo stato della connessione Wi-Fi corrente"""
    if IS_RASPBERRY:
        try:
            output = subprocess.check_output(['iwconfig'], stderr=subprocess.DEVNULL, encoding='utf-8')
            connected = False
            ssid, strength = None, 0

            for line in output.splitlines():
                line = line.strip()
                if "ESSID" in line:
                    if "off/any" not in line and 'ESSID:""' not in line:
                        connected = True
                        ssid = line.split('ESSID:')[1].strip().strip('"')
                if "Signal level" in line:
                    try:
                        level = int(line.split("level=")[1].split()[0].replace("dBm", ""))
                        strength = max(0, min(100, 2 * (level + 100)))
                    except:
                        pass

            ip = "--.--.--.--"
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.connect(("8.8.8.8", 80))
                    ip = s.getsockname()[0]
            except Exception:
                pass

            return {"connected": connected, "ssid": ssid, "strength": strength, "ip": ip}
        except Exception as e:
            print(f"[Network] Errore status: {e}")
            return {"connected": False, "ssid": None, "strength": 0, "ip": "--.--.--.--"}
    else:
        return {"connected": True, "ssid": "Office_Net", "strength": 72, "ip": "192.168.1.1"}
