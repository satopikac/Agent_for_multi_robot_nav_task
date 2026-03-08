from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class SemanticObject:
    obj_id: str
    name: str
    aliases: List[str]
    category: str
    room: str
    position: Tuple[float, float, float]
    description: str = ""

    def all_keywords(self) -> List[str]:
        return [self.name, *self.aliases, self.category, self.room]


@dataclass
class SubTask:
    action: str
    target_name: str
    reason: str = ""
    target_obj_id: Optional[str] = None


@dataclass
class TaskPlan:
    original_instruction: str
    subtasks: List[SubTask] = field(default_factory=list)
    notes: str = ""


@dataclass
class ExecutionRecord:
    step_index: int
    action: str
    target_name: str
    target_obj_id: Optional[str]
    success: bool
    message: str = ""


@dataclass
class ProgressSnapshot:
    original_instruction: str
    completed: List[Dict[str, str]]
    in_progress: Optional[Dict[str, str]]
    pending: List[Dict[str, str]]

