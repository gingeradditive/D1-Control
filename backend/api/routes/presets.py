import json
import os
import uuid
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter()

PRESETS_FILE = "presets.json"

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


class PresetUpdate(BaseModel):
    name: Optional[str] = None
    temperature: Optional[float] = None


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


@router.get("/")
def get_all_presets():
    user_presets = _read_user_presets()
    for p in user_presets:
        p["builtin"] = False
    return HARDCODED_PRESETS + user_presets


@router.post("/")
def create_preset(preset: PresetCreate):
    if preset.temperature < TEMP_MIN or preset.temperature > TEMP_MAX:
        raise HTTPException(status_code=400, detail=f"Temperature must be between {TEMP_MIN} and {TEMP_MAX}°C")
    user_presets = _read_user_presets()
    new_preset = {
        "id": str(uuid.uuid4())[:8],
        "name": preset.name,
        "temperature": preset.temperature,
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
                p["name"] = preset.name
            if preset.temperature is not None:
                p["temperature"] = preset.temperature
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
