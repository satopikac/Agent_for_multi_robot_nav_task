from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .exceptions import ConfigError


DEFAULT_CONFIG: Dict[str, Any] = {
    "llm": {
        "base_url": "https://api.deepseek.com",
        "api_key": "",
        "model": "deepseek-chat",
        "temperature": 0.2,
        "max_tokens": 1024,
        "timeout": 45,
    },
    "memory": {"max_history_turns": 8},
    "planner": {"max_subtasks": 8, "strict_map_only": True},
    "ros": {
        "topic_move_base_goal": "/move_base_simple/goal",
        "topic_move_base_result": "/move_base/result",
        "frame_id": "map",
    },
    "runtime": {"mode": "simulation"},
}


def _merge_dict(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(merged.get(k), dict):
            merged[k] = _merge_dict(merged[k], v)
        else:
            merged[k] = v
    return merged


class Config:
    def __init__(self, data: Dict[str, Any]):
        self._data = data

    @classmethod
    def from_json(cls, path: str | Path) -> "Config":
        path_obj = Path(path)
        if not path_obj.exists():
            raise ConfigError(f"Config file not found: {path_obj}")
        try:
            with path_obj.open("r", encoding="utf-8") as f:
                user_data = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid config JSON: {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to read config file: {e}") from e

        merged = _merge_dict(DEFAULT_CONFIG, user_data)
        return cls(merged)

    def get(self, dotted_key: str, default: Any = None) -> Any:
        if not dotted_key:
            return default
        cur: Any = self._data
        for key in dotted_key.split("."):
            if not isinstance(cur, dict) or key not in cur:
                return default
            cur = cur[key]
        return cur

    def require(self, dotted_key: str) -> Any:
        value = self.get(dotted_key, None)
        if value in (None, ""):
            raise ConfigError(f"Required config missing: {dotted_key}")
        return value

    @property
    def data(self) -> Dict[str, Any]:
        return self._data

