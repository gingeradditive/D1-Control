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
