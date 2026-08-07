import json
import os
import tempfile
import threading
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.core.state import controllers
from backend.core.constants import SETPOINT_TEMP_MIN, SETPOINT_TEMP_MAX

router = APIRouter()

PRESETS_FILE = "presets.json"
MAX_PINNED_PRESETS = 3
DEFAULT_PINNED_PRESET_IDS = ["pla", "petg"]

# Serializza le sequenze leggi->modifica->scrivi su presets.json: os.replace()
# rende atomica solo la sostituzione del file, non l'intera read-modify-write.
_presets_lock = threading.Lock()

HARDCODED_PRESETS = [
    {
        "id": "pla",
        "name": "PLA",
        "temperature": 50,
        "builtin": True,
    },
    {
        "id": "petg",
        "name": "PETG",
        "temperature": 65,
        "builtin": True,
    },
]


TEMP_MIN = SETPOINT_TEMP_MIN
TEMP_MAX = SETPOINT_TEMP_MAX


class PresetCreate(BaseModel):
    name: str
    temperature: float
    pinned: bool = False


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    temperature: Optional[float] = None
    pinned: Optional[bool] = None


class PinnedPresetsUpdate(BaseModel):
    ids: list[str]


def _read_user_presets() -> list[dict]:
    if not os.path.exists(PRESETS_FILE):
        return []
    try:
        with open(PRESETS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return []


def _write_user_presets(presets: list[dict]) -> None:
    dir_ = os.path.dirname(os.path.abspath(PRESETS_FILE))
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile("w", dir=dir_, delete=False, suffix=".tmp") as tmp:
            json.dump(presets, tmp, indent=4)
            tmp.flush()
            os.fsync(tmp.fileno())
            tmp_path = tmp.name
        os.replace(tmp_path, PRESETS_FILE)
    except Exception as e:
        print(f"[Presets] Errore nel salvare {PRESETS_FILE}: {e}")
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass


def _normalize_pinned_ids(ids: list[str], available_ids: set[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for preset_id in ids:
        if preset_id in available_ids and preset_id not in seen:
            normalized.append(preset_id)
            seen.add(preset_id)
        if len(normalized) >= MAX_PINNED_PRESETS:
            break
    return normalized


def _all_presets() -> list[dict]:
    user_presets = _read_user_presets()
    for p in user_presets:
        p["builtin"] = False
    return HARDCODED_PRESETS + user_presets


def _set_pinned(preset_id: str, pinned: bool) -> None:
    """`pinned_preset_ids` in config è l'unica fonte di verità per lo stato pinned."""
    pinned_ids = _get_pinned_ids()
    if pinned:
        if preset_id not in pinned_ids and len(pinned_ids) < MAX_PINNED_PRESETS:
            controllers["config"].set("pinned_preset_ids", pinned_ids + [preset_id])
    else:
        if preset_id in pinned_ids:
            controllers["config"].set("pinned_preset_ids", [i for i in pinned_ids if i != preset_id])


def _get_pinned_ids() -> list[str]:
    config = controllers["config"]
    all_presets = _all_presets()
    available_ids = {p["id"] for p in all_presets}

    raw_ids = config.all().get("pinned_preset_ids", DEFAULT_PINNED_PRESET_IDS)
    if not isinstance(raw_ids, list):
        raw_ids = DEFAULT_PINNED_PRESET_IDS

    normalized_ids = _normalize_pinned_ids(raw_ids, available_ids)
    if normalized_ids != raw_ids:
        config.set("pinned_preset_ids", normalized_ids)
    return normalized_ids


@router.get("/")
def get_all_presets():
    all_presets = _all_presets()
    pinned_ids = set(_get_pinned_ids())
    for p in all_presets:
        p["pinned"] = p["id"] in pinned_ids
    return all_presets


@router.get("/pinned")
def get_pinned_presets():
    return {"ids": _get_pinned_ids()}


@router.put("/pinned")
def update_pinned_presets(payload: PinnedPresetsUpdate):
    if len(payload.ids) > MAX_PINNED_PRESETS:
        raise HTTPException(status_code=400, detail=f"You can pin at most {MAX_PINNED_PRESETS} presets")

    all_presets = _all_presets()
    available_ids = {p["id"] for p in all_presets}

    unknown_ids = [preset_id for preset_id in payload.ids if preset_id not in available_ids]
    if unknown_ids:
        raise HTTPException(status_code=400, detail=f"Unknown preset ids: {', '.join(unknown_ids)}")

    normalized_ids = _normalize_pinned_ids(payload.ids, available_ids)
    controllers["config"].set("pinned_preset_ids", normalized_ids)
    return {"ids": normalized_ids}


@router.post("/")
def create_preset(preset: PresetCreate):
    if preset.temperature < TEMP_MIN or preset.temperature > TEMP_MAX:
        raise HTTPException(status_code=400, detail=f"Temperature must be between {TEMP_MIN} and {TEMP_MAX}°C")
    with _presets_lock:
        all_presets = HARDCODED_PRESETS + _read_user_presets()
        if any(p["name"].strip().lower() == preset.name.strip().lower() for p in all_presets):
            raise HTTPException(status_code=409, detail=f"A preset named '{preset.name}' already exists")
        user_presets = _read_user_presets()
        new_preset = {
            "id": str(uuid.uuid4())[:8],
            "name": preset.name,
            "temperature": preset.temperature,
            "builtin": False,
        }
        user_presets.append(new_preset)
        _write_user_presets(user_presets)

    if preset.pinned:
        _set_pinned(new_preset["id"], True)

    new_preset["pinned"] = new_preset["id"] in _get_pinned_ids()
    return new_preset


@router.put("/{preset_id}")
def update_preset(preset_id: str, preset: PresetUpdate):
    # Cannot edit builtin presets
    for bp in HARDCODED_PRESETS:
        if bp["id"] == preset_id:
            raise HTTPException(status_code=400, detail="Cannot modify built-in presets")

    if preset.temperature is not None and (preset.temperature < TEMP_MIN or preset.temperature > TEMP_MAX):
        raise HTTPException(status_code=400, detail=f"Temperature must be between {TEMP_MIN} and {TEMP_MAX}°C")

    with _presets_lock:
        user_presets = _read_user_presets()
        for p in user_presets:
            if p["id"] == preset_id:
                if preset.name is not None:
                    all_presets = HARDCODED_PRESETS + user_presets
                    if any(p2["name"].strip().lower() == preset.name.strip().lower() and p2["id"] != preset_id for p2 in all_presets):
                        raise HTTPException(status_code=409, detail=f"A preset named '{preset.name}' already exists")
                    p["name"] = preset.name
                if preset.temperature is not None:
                    p["temperature"] = preset.temperature
                _write_user_presets(user_presets)
                break
        else:
            raise HTTPException(status_code=404, detail="Preset not found")

    if preset.pinned is not None:
        _set_pinned(preset_id, preset.pinned)
    p["builtin"] = False
    p["pinned"] = preset_id in _get_pinned_ids()
    return p


@router.delete("/{preset_id}")
def delete_preset(preset_id: str):
    for bp in HARDCODED_PRESETS:
        if bp["id"] == preset_id:
            raise HTTPException(status_code=400, detail="Cannot delete built-in presets")

    with _presets_lock:
        user_presets = _read_user_presets()
        new_presets = [p for p in user_presets if p["id"] != preset_id]
        if len(new_presets) == len(user_presets):
            raise HTTPException(status_code=404, detail="Preset not found")

        _write_user_presets(new_presets)
    return {"status": "deleted"}
