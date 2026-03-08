from __future__ import annotations

import json
from dataclasses import asdict
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .exceptions import SemanticMapError
from .models import SemanticObject


class SemanticMap:
    def __init__(self, objects: List[SemanticObject]):
        self.objects = objects
        self._id_index = {o.obj_id: o for o in objects}

    @classmethod
    def from_json(cls, path: str | Path) -> "SemanticMap":
        path_obj = Path(path)
        if not path_obj.exists():
            raise SemanticMapError(f"Semantic map not found: {path_obj}")

        try:
            with path_obj.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise SemanticMapError(f"Invalid semantic map JSON: {e}") from e
        except OSError as e:
            raise SemanticMapError(f"Failed to read semantic map: {e}") from e

        if not isinstance(data, dict) or "objects" not in data:
            raise SemanticMapError("Semantic map must contain top-level key 'objects'.")

        objects: List[SemanticObject] = []
        for idx, item in enumerate(data.get("objects", [])):
            try:
                position = item["position"]
                objects.append(
                    SemanticObject(
                        obj_id=str(item["id"]),
                        name=str(item["name"]),
                        aliases=[str(a) for a in item.get("aliases", [])],
                        category=str(item.get("category", "")),
                        room=str(item.get("room", "")),
                        position=(float(position["x"]), float(position["y"]), float(position.get("yaw", 0.0))),
                        description=str(item.get("description", "")),
                    )
                )
            except (KeyError, TypeError, ValueError) as e:
                raise SemanticMapError(f"Invalid object at index {idx}: {e}") from e

        if not objects:
            raise SemanticMapError("Semantic map has no objects.")
        return cls(objects)

    def as_prompt_brief(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": obj.obj_id,
                "name": obj.name,
                "aliases": obj.aliases,
                "category": obj.category,
                "room": obj.room,
                "description": obj.description,
            }
            for obj in self.objects
        ]

    def find_by_id(self, obj_id: str) -> Optional[SemanticObject]:
        return self._id_index.get(obj_id)

    def _string_score(self, a: str, b: str) -> float:
        if not a or not b:
            return 0.0
        a_l, b_l = a.lower(), b.lower()
        if a_l == b_l:
            return 1.0
        if a_l in b_l or b_l in a_l:
            return 0.9
        return SequenceMatcher(None, a_l, b_l).ratio()

    def match_object(self, query: str, threshold: float = 0.48) -> Tuple[Optional[SemanticObject], float]:
        query = (query or "").strip()
        if not query:
            return None, 0.0

        best_obj: Optional[SemanticObject] = None
        best_score = 0.0
        for obj in self.objects:
            candidates = obj.all_keywords()
            score = max((self._string_score(query, cand) for cand in candidates), default=0.0)

            query_tokens = [tok for tok in query.lower().split() if tok]
            if query_tokens:
                for tok in query_tokens:
                    if any(tok in c.lower() for c in candidates):
                        score = max(score, 0.72)
            if score > best_score:
                best_score = score
                best_obj = obj

        if best_score < threshold:
            return None, best_score
        return best_obj, best_score

