import subprocess
import time

try:
    import RPi.GPIO as GPIO
    IS_RASPBERRY = True
except (ImportError, NotImplementedError):
    IS_RASPBERRY = False
    print("[Network] RPi.GPIO not available, running in simulation mode.")


def get_networks():
    """Scansiona le reti Wi-Fi disponibili e restituisce una lista di dict"""
    if IS_RASPBERRY:
        try:
            output = subprocess.check_output(
                ['nmcli', '-t', '-f', 'SSID,SIGNAL', 'dev', 'wifi'],
                encoding='utf-8'
            )
            network_map = {}
            for line in output.strip().split('\n'):
                if line:
                    ssid, signal = line.split(":", 1)
                    if ssid:
                        signal = int(signal)
                        # mantieni solo la rete con segnale più forte per SSID duplicati
                        if ssid not in network_map or signal > network_map[ssid]:
                            network_map[ssid] = signal

            return [{"ssid": ssid, "strength": signal} for ssid, signal in network_map.items()]
        except Exception as e:
            print(f"[Network] Error retrieving Wi-Fi networks: {e}")
            return []
    else:
        print("[Network] Simulation: slow Wi-Fi scan (10s)...")
        time.sleep(10)
        return [
            {"ssid": "Home_WiFi", "strength": 65},
            {"ssid": "Office_Net", "strength": 80},
            {"ssid": "Cafe_Free_WiFi", "strength": 40},
        ]
