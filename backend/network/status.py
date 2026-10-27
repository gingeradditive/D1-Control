import subprocess

from backend.core.platform import IS_RASPBERRY

if not IS_RASPBERRY:
    print("[Network] Not running on a Raspberry Pi, running in simulation mode.")

NO_IP = "--.--.--.--"


def _nmcli(*args) -> list[list[str]]:
    """Esegue nmcli in modalità terse e restituisce le righe già divise sui ':'."""
    output = subprocess.check_output(
        ['nmcli', '-t', *args], stderr=subprocess.DEVNULL, encoding='utf-8', timeout=10
    )
    # nei campi i ':' sono escapati come '\:' (es. SSID)
    rows = []
    for line in output.splitlines():
        if line:
            rows.append([f.replace('\x00', ':') for f in line.replace('\\:', '\x00').split(':')])
    return rows


def _device_ip(device: str) -> str:
    try:
        for row in _nmcli('-g', 'IP4.ADDRESS', 'device', 'show', device):
            if row and row[0]:
                return row[0].split('/')[0]
    except Exception:
        pass
    return NO_IP


def get_status() -> dict:
    """Stato della rete: Wi-Fi (connected/ssid/strength/ip) e cavo (ethernet).

    Prima si leggeva solo iwconfig, quindi una macchina collegata via cavo
    risultava "non connessa" e l'operatore era costretto a configurare anche
    il Wi-Fi. NetworkManager vede entrambe le interfacce.
    """
    if IS_RASPBERRY:
        status = {"connected": False, "ssid": None, "strength": 0, "ip": NO_IP,
                  "ethernet": {"connected": False, "ip": NO_IP}}
        try:
            for device, dev_type, state, connection in _nmcli('-f', 'DEVICE,TYPE,STATE,CONNECTION', 'device'):
                if state != 'connected':
                    continue
                if dev_type == 'ethernet' and not status["ethernet"]["connected"]:
                    status["ethernet"] = {"connected": True, "ip": _device_ip(device)}
                elif dev_type == 'wifi' and not status["connected"]:
                    status.update(connected=True, ssid=connection, ip=_device_ip(device))

            if status["connected"]:
                # --rescan no: legge l'ultimo scan senza bloccare per una nuova scansione
                for active, ssid, signal in _nmcli('-f', 'ACTIVE,SSID,SIGNAL', 'device', 'wifi', 'list', '--rescan', 'no'):
                    if active == 'yes':
                        status["ssid"] = ssid or status["ssid"]
                        status["strength"] = int(signal or 0)
                        break
        except Exception as e:
            print(f"[Network] Status error: {e}")
        return status
    else:
        return {"connected": True, "ssid": "Office_Net", "strength": 72, "ip": "192.168.1.1",
                "ethernet": {"connected": False, "ip": NO_IP}}
