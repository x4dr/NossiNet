import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional


class MechaEncounterManager:
    def __init__(self, wiki_root: Path, mecha_id: str):
        self.encounter_dir = wiki_root / "encounters"
        self.mecha_id = mecha_id.replace("/", "_")
        self.encounter_dir.mkdir(parents=True, exist_ok=True)

    def _get_filename(self, timestamp: str) -> Path:
        return self.encounter_dir / f"mecha_{self.mecha_id}_{timestamp}_encounter.json"

    def start_new_encounter(self, custom_name: Optional[str] = None) -> str:
        # Format: weekday-day-month-year-hh:mm
        # Using a filesystem-safe version for the filename: YYYYMMDD_HHMMSS
        now = datetime.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S")
        display_name = custom_name or now.strftime("%A-%d-%m-%y-%H:%M")

        filename = self._get_filename(timestamp)
        data = {
            "mecha_id": self.mecha_id,
            "name": display_name,
            "start_time": now.isoformat(),
            "events": [{"type": "LOADOUT_APPLY", "name": "Default"}],
        }

        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

        return timestamp

    def list_encounters(self) -> List[Dict[str, Any]]:
        encounters = []
        prefix = f"mecha_{self.mecha_id}_"
        for f in self.encounter_dir.glob(f"{prefix}*_encounter.json"):
            try:
                with open(f, "r") as file:
                    data = json.load(file)
                    timestamp = f.name[len(prefix) : -len("_encounter.json")]
                    encounters.append(
                        {
                            "id": timestamp,
                            "name": data.get("name", timestamp),
                            "start_time": data.get("start_time"),
                            "file": f.name,
                        }
                    )
            except (json.JSONDecodeError, IOError):
                continue

        # Sort by start_time descending
        encounters.sort(key=lambda x: x["start_time"] or "", reverse=True)
        return encounters

    def load_encounter(self, timestamp: str) -> Optional[Dict[str, Any]]:
        filename = self._get_filename(timestamp)
        if not filename.exists():
            return None
        try:
            with open(filename, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def save_encounter(self, timestamp: str, data: Dict[str, Any]):
        filename = self._get_filename(timestamp)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def rename_encounter(self, timestamp: str, new_name: str):
        data = self.load_encounter(timestamp)
        if data:
            data["name"] = new_name
            self.save_encounter(timestamp, data)

    def log_event(self, timestamp: str, event: Dict[str, Any]):
        data = self.load_encounter(timestamp)
        if data:
            data["events"].append(event)
            self.save_encounter(timestamp, data)

    def truncate_log(self, timestamp: str, turn_limit: int):
        data = self.load_encounter(timestamp)
        if not data:
            return

        new_events = []
        for event in data.get("events", []):
            new_events.append(event)
            if (
                event.get("type") == "TURN_COMMIT"
                and event.get("turn", 0) >= turn_limit
            ):
                break

        data["events"] = new_events
        self.save_encounter(timestamp, data)

    def get_latest_encounter_id(self) -> Optional[str]:
        encounters = self.list_encounters()
        return encounters[0]["id"] if encounters else None
