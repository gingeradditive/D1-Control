from backend.network import status as net_status


def _fake_nmcli(outputs):
    def check_output(cmd, **kwargs):
        key = " ".join(cmd[2:])
        return outputs.get(key, "")
    return check_output


def test_ethernet_only_is_reported(monkeypatch):
    monkeypatch.setattr(net_status, "IS_RASPBERRY", True)
    monkeypatch.setattr(net_status.subprocess, "check_output", _fake_nmcli({
        "-f DEVICE,TYPE,STATE,CONNECTION device":
            "eth0:ethernet:connected:Wired connection 1\nwlan0:wifi:disconnected:\nlo:loopback:connected (externally):lo\n",
        "-g IP4.ADDRESS device show eth0": "192.168.1.146/24\n",
    }))

    st = net_status.get_status()

    assert st["ethernet"] == {"connected": True, "ip": "192.168.1.146"}
    assert st["connected"] is False


def test_wifi_with_escaped_ssid(monkeypatch):
    monkeypatch.setattr(net_status, "IS_RASPBERRY", True)
    monkeypatch.setattr(net_status.subprocess, "check_output", _fake_nmcli({
        "-f DEVICE,TYPE,STATE,CONNECTION device": "wlan0:wifi:connected:Lab\\:2\n",
        "-g IP4.ADDRESS device show wlan0": "10.0.0.5/24\n",
        "-f ACTIVE,SSID,SIGNAL device wifi list --rescan no": "no:Other:90\nyes:Lab\\:2:64\n",
    }))

    st = net_status.get_status()

    assert st["ethernet"]["connected"] is False
    assert (st["connected"], st["ssid"], st["strength"], st["ip"]) == (True, "Lab:2", 64, "10.0.0.5")
