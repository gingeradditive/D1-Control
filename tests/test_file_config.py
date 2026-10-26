"""FileConfig concorrente: prima del threading.Lock, due set() simultanei
potevano perdersi a vicenda (leggi->modifica->scrivi non atomico)."""
import threading

from backend.core.config.file_config import FileConfig


def test_concurrent_set_does_not_lose_updates(tmp_path):
    config = FileConfig(path=str(tmp_path / "config.json"))
    n_threads = 20

    def worker(i):
        config.set(f"key_{i}", i)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    data = config.all()
    for i in range(n_threads):
        assert data[f"key_{i}"] == i


def test_set_normalizes_numeric_strings(tmp_path):
    config = FileConfig(path=str(tmp_path / "config.json"))

    config.set("as_int", "42")
    config.set("as_float", "3.14")
    config.set("not_numeric", "hello")

    data = config.all()
    assert data["as_int"] == 42
    assert data["as_float"] == 3.14
    assert data["not_numeric"] == "hello"


def test_get_returns_default_for_missing_key(tmp_path):
    config = FileConfig(path=str(tmp_path / "config.json"))

    assert config.get("missing", 7, int) == 7


def test_migrates_purge_and_cycle_from_seconds_to_minutes(tmp_path):
    import json
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"purge_time": 60, "cycle_time": 3600}))

    config = FileConfig(path=str(path))

    assert config.get("purge_time", 0, int) == 1
    assert config.get("cycle_time", 0, int) == 60
    assert json.loads(path.read_text())["cycle_time"] == 60


def test_keeps_purge_and_cycle_already_in_minutes(tmp_path):
    import json
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"purge_time": 2, "cycle_time": 90}))

    config = FileConfig(path=str(path))

    assert config.get("purge_time", 0, int) == 2
    assert config.get("cycle_time", 0, int) == 90
