import json
import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from backend.core.state import controllers

router = APIRouter()

PRESETS_FILE = "presets.json"
MAX_PINNED_PRESETS = 3
DEFAULT_PINNED_PRESET_IDS = ["pla", "petg"]

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


TEMP_MIN = 0
TEMP_MAX = 70


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
    with open(PRESETS_FILE, "w") as f:
        json.dump(presets, f, indent=4)


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
    all_presets = HARDCODED_PRESETS + _read_user_presets()
    if any(p["name"].strip().lower() == preset.name.strip().lower() for p in all_presets):
        raise HTTPException(status_code=409, detail=f"A preset named '{preset.name}' already exists")
    user_presets = _read_user_presets()
    new_preset = {
        "id": str(uuid.uuid4())[:8],
        "name": preset.name,
        "temperature": preset.temperature,
        "pinned": preset.pinned,
        "builtin": False,
    }
    user_presets.append(new_preset)
    _write_user_presets(user_presets)
    return new_preset


@router.put("/{preset_id}")
def update_preset(preset_id: str, preset: PresetUpdate):
    # Cannot edit builtin presets
    for bp in HARDCODED_PRESETS:
        if bp["id"] == preset_id:
            raise HTTPException(status_code=400, detail="Cannot modify built-in presets")

    if preset.temperature is not None and (preset.temperature < TEMP_MIN or preset.temperature > TEMP_MAX):
        raise HTTPException(status_code=400, detail=f"Temperature must be between {TEMP_MIN} and {TEMP_MAX}°C")

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
            if preset.pinned is not None:
                p["pinned"] = preset.pinned
            _write_user_presets(user_presets)
            p["builtin"] = False
            return p

    raise HTTPException(status_code=404, detail="Preset not found")


@router.delete("/{preset_id}")
def delete_preset(preset_id: str):
    for bp in HARDCODED_PRESETS:
        if bp["id"] == preset_id:
            raise HTTPException(status_code=400, detail="Cannot delete built-in presets")

    user_presets = _read_user_presets()
    new_presets = [p for p in user_presets if p["id"] != preset_id]
    if len(new_presets) == len(user_presets):
        raise HTTPException(status_code=404, detail="Preset not found")

    _write_user_presets(new_presets)
    return {"status": "deleted"}
