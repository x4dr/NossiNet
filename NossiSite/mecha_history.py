"""Encounter history management for Mecha combat encounters."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class MechaEncounterManager:
    """Manages creation, retrieval, and modification of mecha combat encounters."""

    def __init__(self, wiki_root: Path, mecha_id: str):
        """Initialize the encounter manager.

        Args:
            wiki_root: Root path of the wiki.
            mecha_id: Identifier for the mecha character.
        """
        self.encounter_dir = wiki_root / "encounters"
        self.mecha_id = mecha_id.replace("/", "_")
        self.encounter_dir.mkdir(parents=True, exist_ok=True)

    def _get_filename(self, timestamp: str) -> Path:
        return self.encounter_dir / f"mecha_{self.mecha_id}_{timestamp}_encounter.json"

    def start_new_encounter(self, custom_name: str | None = None) -> str:
        """Create and persist a new encounter with an optional display name.

        Args:
            custom_name: Optional human-readable name for the encounter.

        Returns:
            The timestamp string used as the encounter ID.
        """
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

    def list_encounters(self) -> list[dict[str, Any]]:
        """List all encounters for this mecha, sorted newest first.

        Returns:
            A list of encounter summary dicts with id, name, start_time, file.
        """
        encounters = []
        prefix = f"mecha_{self.mecha_id}_"
        for f in self.encounter_dir.glob(f"{prefix}*_encounter.json"):
            try:
                with open(f) as file:
                    data = json.load(file)
                    timestamp = f.name[len(prefix) : -len("_encounter.json")]
                    encounters.append(
                        {
                            "id": timestamp,
                            "name": data.get("name", timestamp),
                            "start_time": data.get("start_time"),
                            "file": f.name,
                        },
                    )
            except (OSError, json.JSONDecodeError):
                continue

        # Sort by start_time descending
        encounters.sort(key=lambda x: x["start_time"] or "", reverse=True)
        return encounters

    def load_encounter(self, timestamp: str) -> dict[str, Any] | None:
        """Load an encounter by its timestamp ID.

        Args:
            timestamp: The encounter ID (filename timestamp).

        Returns:
            The encounter data dict, or None if not found.
        """
        filename = self._get_filename(timestamp)
        if not filename.exists():
            return None
        try:
            with open(filename) as f:
                result = json.load(f)
                assert isinstance(result, dict)
                return result
        except (OSError, json.JSONDecodeError):
            return None

    def save_encounter(self, timestamp: str, data: dict[str, Any]) -> None:
        """Persist encounter data to disk.

        Args:
            timestamp: The encounter ID.
            data: Full encounter data dict to save.
        """
        filename = self._get_filename(timestamp)
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)

    def rename_encounter(self, timestamp: str, new_name: str) -> None:
        """Update the display name of an encounter.

        Args:
            timestamp: The encounter ID.
            new_name: New display name.
        """
        data = self.load_encounter(timestamp)
        if data:
            data["name"] = new_name
            self.save_encounter(timestamp, data)

    def log_event(self, timestamp: str, event: dict[str, Any]) -> None:
        """Append an event to the encounter's event log.

        Args:
            timestamp: The encounter ID.
            event: Event dict to append.
        """
        data = self.load_encounter(timestamp)
        if data:
            data["events"].append(event)
            self.save_encounter(timestamp, data)

    def truncate_log(self, timestamp: str, turn_limit: int) -> None:
        """Remove events after a given turn limit from the encounter log.

        Args:
            timestamp: The encounter ID.
            turn_limit: Maximum turn number to retain.
        """
        data = self.load_encounter(timestamp)
        if not data:
            return

        new_events = []
        for event in data.get("events", []):
            new_events.append(event)
            if event.get("type") == "TURN_COMMIT" and event.get("turn", 0) >= turn_limit:
                break

        data["events"] = new_events
        self.save_encounter(timestamp, data)

    def get_latest_encounter_id(self) -> str | None:
        """Return the ID of the most recent encounter, or None if none exist."""
        encounters = self.list_encounters()
        return encounters[0]["id"] if encounters else None
