"""Test di regressione partiti dall'audit in TODO.md: il bug che ha innescato
l'audit (background_loop bloccato, history che smette di crescere) sarebbe
stato preso dal primo test qui sotto.
"""
import time
from datetime import datetime

import pytest

from backend.core.background import background_loop
from backend.core.config.file_config import FileConfig
from backend.dryer.controller import DryerController


@pytest.fixture
def dryer(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = FileConfig(path=str(tmp_path / "config.json"))
    return DryerController(config)


def test_background_loop_grows_history(dryer, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)  # niente attesa reale a 1Hz
    controllers = {"dryer": dryer}

    calls = {"n": 0}

    def is_running():
        calls["n"] += 1
        return calls["n"] <= 15

    background_loop(controllers, is_running)

    assert len(dryer.history) >= 10


def test_read_sensor_valid_reading_appends_to_history(dryer):
    dryer.sensors.read_all = lambda: (datetime.now(), 42.0)
    now, temp = dryer.read_sensor()

    assert temp == 42.0
    assert len(dryer.history) == 1
    assert dryer.sensor_fault is False


def test_read_sensor_invalid_reading_trips_fault_after_streak(dryer):
    dryer.sensors.read_all = lambda: (datetime.now(), 9999.0)  # open thermocouple

    for _ in range(2):
        dryer.read_sensor()
    assert dryer.sensor_fault is False  # sotto la soglia di trip

    dryer.read_sensor()
    assert dryer.sensor_fault is True
    assert dryer.sensor_fault_desc in dryer.errors.snapshot()


def test_read_sensor_fault_clears_after_good_streak(dryer):
    dryer.sensors.read_all = lambda: (datetime.now(), 9999.0)
    for _ in range(3):
        dryer.read_sensor()
    assert dryer.sensor_fault is True

    dryer.sensors.read_all = lambda: (datetime.now(), 42.0)
    for _ in range(5):
        dryer.read_sensor()

    assert dryer.sensor_fault is False
    assert dryer.errors.snapshot() == {}


def test_update_heater_respects_hysteresis(dryer):
    dryer.dryer_status = True
    dryer.set_temp = 50.0
    dryer.tolerance = 1.5
    dryer.heater_off_duration = 0
    dryer.last_heater_toggle = time.monotonic() - 999

    dryer.update_heater(47.0)  # sotto (setpoint - tolerance) -> deve accendersi
    assert dryer.heater.is_on() is True

    dryer.update_heater(50.0)  # >= setpoint -> deve spegnersi
    assert dryer.heater.is_on() is False


def test_update_heater_stays_off_while_valve_open(dryer):
    dryer.dryer_status = True
    dryer.set_temp = 50.0
    dryer.tolerance = 1.5
    dryer.heater_off_duration = 0
    dryer.last_heater_toggle = time.monotonic() - 999
    dryer.valve._is_open = True

    dryer.update_heater(30.0)  # molto sotto il setpoint, ma valvola aperta

    assert dryer.heater.is_on() is False


def test_accumulate_session_hours(dryer):
    dryer.session_start_time = time.monotonic() - 3600  # un'ora fa
    dryer.total_hours = 0.0
    dryer.filter_hours = 0.0

    dryer._accumulate_session_hours()

    assert dryer.total_hours == pytest.approx(1.0, abs=0.01)
    assert dryer.filter_hours == pytest.approx(1.0, abs=0.01)
    assert dryer.session_start_time is None


def test_accumulate_session_hours_noop_when_not_started(dryer):
    dryer.session_start_time = None
    dryer.total_hours = 5.0

    dryer._accumulate_session_hours()

    assert dryer.total_hours == 5.0


# --- stop automatici e diagnostica dei riavvii -------------------------------
# Sul campo il ciclo si fermava di notte senza lasciare traccia: gli stop
# automatici devono restare visibili anche quando la causa è rientrata.

def _auto_stop_keys(dryer):
    return [k for k in dryer.errors.snapshot() if k.startswith("Drying cycle stopped automatically")]


def test_sensor_fault_stop_leaves_sticky_warning_after_fault_clears(dryer):
    dryer.start()
    dryer.sensors.read_all = lambda: (datetime.now(), 9999.0)
    for _ in range(3):
        dryer.read_sensor()
    assert dryer.dryer_status is False

    dryer.sensors.read_all = lambda: (datetime.now(), 42.0)
    for _ in range(5):
        dryer.read_sensor()

    assert dryer.sensor_fault is False
    keys = _auto_stop_keys(dryer)
    assert len(keys) == 1 and "sensor fault" in keys[0]

    dryer.start()  # l'operatore riparte: l'avviso si considera letto
    assert _auto_stop_keys(dryer) == []


def test_manual_stop_does_not_leave_auto_stop_warning(dryer):
    dryer.start()
    dryer.stop()
    assert _auto_stop_keys(dryer) == []


def test_watchdog_trip_stop_persists_after_loop_recovers(dryer):
    from backend.core.watchdog import ControlLoopWatchdog

    dryer.start()
    watchdog = ControlLoopWatchdog({"dryer": dryer}, lambda: False, timeout=5)

    dryer._last_loop_beat = time.monotonic() - 10
    watchdog._check()
    assert dryer.dryer_status is False

    dryer.heartbeat()
    watchdog._check()
    keys = _auto_stop_keys(dryer)
    assert len(keys) == 1 and "control loop stalled" in keys[0]


def test_background_loop_refreshes_heartbeat_on_start(dryer, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)
    dryer._last_loop_beat = time.monotonic() - 60  # avvio lento di uvicorn
    background_loop({"dryer": dryer}, lambda: False)
    assert dryer.loop_heartbeat_age() < 1


def test_valve_error_does_not_block_sensor_and_heater(dryer, monkeypatch):
    monkeypatch.setattr(time, "sleep", lambda s: None)

    def broken_valve():
        raise OSError("GPIO busy")

    dryer.update_valve = broken_valve
    calls = {"n": 0}

    def is_running():
        calls["n"] += 1
        return calls["n"] <= 5

    background_loop({"dryer": dryer}, is_running)

    assert len(dryer.history) == 5
    assert any("Valve error" in k for k in dryer.errors.snapshot())


def test_unexpected_restart_warning_after_power_loss(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    config = FileConfig(path=str(tmp_path / "config.json"))
    DryerController(config).start()

    # nessuno stop(): il processo muore con il ciclo acceso (taglio di corrente)
    restarted = DryerController(FileConfig(path=str(tmp_path / "config.json")))

    assert restarted.dryer_status is False
    assert "Previous drying cycle was interrupted by an unexpected restart" in restarted.errors.snapshot()


# --- alimentazione -----------------------------------------------------------

def test_power_monitor_flags_undervoltage(dryer):
    from backend.core.power import PowerMonitor, UNDERVOLTAGE_KEY

    readings = iter([0x0, 0x50005])
    monitor = PowerMonitor(dryer.errors, reader=lambda: next(readings))

    monitor.check()
    assert UNDERVOLTAGE_KEY not in dryer.errors.snapshot()

    monitor.check()
    assert UNDERVOLTAGE_KEY in dryer.errors.snapshot()


# --- valvola -----------------------------------------------------------------

def test_valve_ramp_moves_in_small_steps():
    from backend.dryer.components.valve import Valve, RAMP_STEP_DEG

    steps = Valve._ramp(10.0, 100.0)
    assert steps[-1] == 100.0
    deltas = [b - a for a, b in zip([10.0] + steps, steps)]
    assert all(0 < d <= RAMP_STEP_DEG for d in deltas)

    assert Valve._ramp(100.0, 10.0)[-1] == 10.0
    assert Valve._ramp(None, 100.0) == [100.0]  # posizione ignota al boot


def test_heater_waits_for_valve_to_settle(dryer):
    dryer.dryer_status = True
    dryer.set_temp = 50.0
    dryer.tolerance = 1.5
    dryer.heater_off_duration = 0
    dryer.last_heater_toggle = time.monotonic() - 999

    dryer.valve.close()  # appena mosso: la 5V si sta ancora riprendendo
    dryer.update_heater(30.0)
    assert dryer.heater.is_on() is False

    dryer.valve._last_move_end = time.monotonic() - 60
    dryer.update_heater(30.0)
    assert dryer.heater.is_on() is True
